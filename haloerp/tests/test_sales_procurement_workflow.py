# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from haloerp.controllers.sales_procurement_controller import (
	get_workflow_summary,
	get_item_quantity_breakdown,
	get_quotation_sales_orders,
	create_partial_sales_order,
	create_multi_supplier_purchase_orders,
	get_pending_fulfillment_overview,
	get_traceability_graph,
)


class TestSalesProcurementWorkflow(FrappeTestCase):
	def setUp(self):
		self.company = "_Test Company"
		if not frappe.db.exists("Company", self.company):
			from haloerp.setup.doctype.company.test_company import create_test_company
			create_test_company(company_name=self.company)

	def test_pending_fulfillment_overview(self):
		res = get_pending_fulfillment_overview({"company": self.company})
		self.assertIn("counts", res)
		self.assertIn("procurement_required", res["counts"])
		self.assertIn("pending_receipts", res["counts"])
		self.assertIn("ready_for_delivery", res["counts"])
		self.assertIn("pending_invoices", res["counts"])
		self.assertIn("outstanding_invoices", res["counts"])
