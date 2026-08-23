# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import frappe


@frappe.whitelist()
def get_initial_context():
	return {
		"company": frappe.defaults.get_user_default("company"),
	}
