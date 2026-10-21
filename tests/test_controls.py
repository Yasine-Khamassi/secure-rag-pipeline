"""
Control tests for the secure-RAG app - no model required, so CI runs them on every
change. They check the access-control boundary, instruction/data separation and the
DLP backstop, plus the store's role filtering.

    python -m unittest discover -s tests -v
"""

import unittest

from app.config import ROLE_EMPLOYEE, ROLE_HR, HR_CANARY, INJECT_CANARY
from defenses.controls import allowed_roles, build_context, validate_output
from app.store import VectorStore, Record


class TestEntitlements(unittest.TestCase):
    def test_employee_cannot_reach_hr(self):
        self.assertNotIn(ROLE_HR, allowed_roles(ROLE_EMPLOYEE))

    def test_hr_can_reach_both(self):
        self.assertEqual(allowed_roles(ROLE_HR), {ROLE_EMPLOYEE, ROLE_HR})


class TestContextSeparation(unittest.TestCase):
    def test_defended_labels_untrusted(self):
        ctx = build_context(["some doc"], defended=True)
        self.assertIn("UNTRUSTED DOCUMENT", ctx)

    def test_vulnerable_is_raw(self):
        ctx = build_context(["some doc"], defended=False)
        self.assertEqual(ctx, "some doc")


class TestDLP(unittest.TestCase):
    def test_redacts_hr_canary(self):
        out, red = validate_output(f"the code is {HR_CANARY} ok")
        self.assertTrue(red)
        self.assertNotIn(HR_CANARY, out)

    def test_passes_clean(self):
        out, red = validate_output("shipping takes 3-5 days")
        self.assertFalse(red)


class TestStoreRoleFilter(unittest.TestCase):
    def _store(self):
        s = VectorStore()
        s.add(Record("pub", ROLE_EMPLOYEE, "internal", "x", [1.0, 0.0]))
        s.add(Record("hr", ROLE_HR, "internal", "y", [0.9, 0.1]))
        return s

    def test_filter_excludes_hr_for_employee(self):
        s = self._store()
        hits = s.search([1.0, 0.0], k=5, allowed_roles={ROLE_EMPLOYEE})
        self.assertEqual([r.id for r, _ in hits], ["pub"])

    def test_no_filter_returns_hr(self):
        s = self._store()
        ids = [r.id for r, _ in s.search([1.0, 0.0], k=5, allowed_roles=None)]
        self.assertIn("hr", ids)


if __name__ == "__main__":
    unittest.main()
