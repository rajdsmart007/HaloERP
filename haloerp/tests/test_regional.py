import frappe

import haloerp
from haloerp.tests.utils import ERPNextTestSuite


@haloerp.allow_regional
def test_method():
	return "original"


class TestInit(ERPNextTestSuite):
	def test_regional_overrides(self):
		frappe.flags.country = "Maldives"
		self.assertEqual(test_method(), "original")
