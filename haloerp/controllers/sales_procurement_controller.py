# Copyright (c) 2026, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt

import json
import frappe
from frappe import _
from frappe.utils import flt, cint, nowdate, add_days, get_link_to_form
from frappe.model.mapper import get_mapped_doc


@frappe.whitelist()
def get_workflow_summary(doctype: str, name: str, customer: str | None = None) -> dict:
	"""
	Returns a full lifecycle summary for a given transaction or customer.
	Connects: Enquiry (Opportunity/Lead) -> Quotation -> Customer PO ->
	Sales Orders -> Purchase Orders -> Purchase Receipts -> Delivery Notes ->
	Sales Invoices -> Payment Entries.
	"""
	if not frappe.has_permission(doctype, "read", doc=name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	summary = {
		"doctype": doctype,
		"name": name,
		"customer": None,
		"customer_name": None,
		"company": None,
		"transaction_date": None,
		"grand_total": 0.0,
		"currency": None,
		"status": None,
		"enquiry": None,
		"quotations": [],
		"customer_pos": [],
		"sales_orders": [],
		"purchase_orders": [],
		"purchase_receipts": [],
		"delivery_notes": [],
		"sales_invoices": [],
		"payments": [],
		"stages": {
			"enquiry": {"status": "gray", "count": 0, "label": _("Customer Enquiry"), "docs": []},
			"quotation": {"status": "gray", "count": 0, "label": _("Quotation"), "docs": []},
			"customer_po": {"status": "gray", "count": 0, "label": _("Customer PO"), "docs": []},
			"sales_order": {"status": "gray", "count": 0, "label": _("Sales Orders"), "docs": []},
			"procurement": {"status": "gray", "count": 0, "label": _("Procurement"), "docs": []},
			"receipt": {"status": "gray", "count": 0, "label": _("Goods Receipt"), "docs": []},
			"delivery": {"status": "gray", "count": 0, "label": _("Customer Delivery"), "docs": []},
			"invoice": {"status": "gray", "count": 0, "label": _("Customer Invoice"), "docs": []},
			"payment": {"status": "gray", "count": 0, "label": _("Payment Received"), "docs": []},
		},
		"metrics": {
			"total_quoted_qty": 0.0,
			"total_ordered_qty": 0.0,
			"total_purchased_qty": 0.0,
			"total_received_qty": 0.0,
			"total_delivered_qty": 0.0,
			"total_invoiced_qty": 0.0,
			"total_paid_amount": 0.0,
			"total_invoiced_amount": 0.0,
		},
	}

	doc = frappe.get_doc(doctype, name)
	summary["company"] = getattr(doc, "company", None)
	summary["customer"] = getattr(doc, "customer", getattr(doc, "party_name", customer))
	summary["customer_name"] = getattr(doc, "customer_name", summary["customer"])
	summary["currency"] = getattr(doc, "currency", None)
	summary["transaction_date"] = getattr(doc, "transaction_date", getattr(doc, "posting_date", None))
	summary["grand_total"] = flt(getattr(doc, "grand_total", getattr(doc, "base_grand_total", 0.0)))
	summary["status"] = getattr(doc, "status", None)

	# Collect all linked Quotations & Sales Orders
	quotation_names = set()
	sales_order_names = set()
	customer_pos = set()

	if doctype == "Quotation":
		quotation_names.add(doc.name)
		if getattr(doc, "opportunity", None):
			summary["enquiry"] = {"doctype": "Opportunity", "name": doc.opportunity}
		# Find SOs linked to this Quotation
		linked_sos = frappe.get_all(
			"Sales Order Item",
			filters={"prevdoc_docname": doc.name, "docstatus": ["!=", 2]},
			fields=["parent"],
			distinct=True,
		)
		for so in linked_sos:
			sales_order_names.add(so.parent)

	elif doctype == "Sales Order":
		sales_order_names.add(doc.name)
		if getattr(doc, "po_no", None):
			customer_pos.add(doc.po_no)
		# Find Quotation if created from one
		for item in getattr(doc, "items", []):
			if getattr(item, "prevdoc_docname", None):
				quotation_names.add(item.prevdoc_docname)

	elif doctype == "Delivery Note":
		for item in getattr(doc, "items", []):
			if getattr(item, "against_sales_order", None):
				sales_order_names.add(item.against_sales_order)

	elif doctype == "Sales Invoice":
		for item in getattr(doc, "items", []):
			if getattr(item, "sales_order", None):
				sales_order_names.add(item.sales_order)

	elif doctype == "Purchase Order":
		for item in getattr(doc, "items", []):
			if getattr(item, "sales_order", None):
				sales_order_names.add(item.sales_order)

	elif doctype == "Purchase Receipt":
		for item in getattr(doc, "items", []):
			if getattr(item, "purchase_order", None):
				po_doc = frappe.get_doc("Purchase Order", item.purchase_order)
				for po_item in po_doc.items:
					if po_item.sales_order:
						sales_order_names.add(po_item.sales_order)

	# Expand Quotation relationships if Quotations found
	for q_name in list(quotation_names):
		q_doc = frappe.get_doc("Quotation", q_name)
		summary["quotations"].append({
			"name": q_doc.name,
			"status": q_doc.status,
			"transaction_date": q_doc.transaction_date,
			"grand_total": q_doc.grand_total,
			"total_qty": sum(flt(i.qty) for i in q_doc.items),
		})
		for item in q_doc.items:
			summary["metrics"]["total_quoted_qty"] += flt(item.qty)
		if q_doc.opportunity and not summary["enquiry"]:
			summary["enquiry"] = {"doctype": "Opportunity", "name": q_doc.opportunity}

		# Also find any remaining Sales Orders
		so_items = frappe.get_all(
			"Sales Order Item",
			filters={"prevdoc_docname": q_name, "docstatus": ["!=", 2]},
			fields=["parent"],
			distinct=True,
		)
		for so in so_items:
			sales_order_names.add(so.parent)

	# Process Sales Orders
	po_names = set()
	dn_names = set()
	sinv_names = set()

	for so_name in list(sales_order_names):
		so_doc = frappe.get_doc("Sales Order", so_name)
		summary["sales_orders"].append({
			"name": so_doc.name,
			"status": so_doc.status,
			"delivery_status": getattr(so_doc, "delivery_status", None),
			"billing_status": getattr(so_doc, "billing_status", None),
			"transaction_date": so_doc.transaction_date,
			"grand_total": so_doc.grand_total,
			"total_qty": sum(flt(i.qty) for i in so_doc.items),
			"delivered_qty": sum(flt(i.delivered_qty) for i in so_doc.items),
			"billed_amt": sum(flt(i.billed_amt) for i in so_doc.items),
			"po_no": so_doc.po_no,
		})
		if so_doc.po_no:
			customer_pos.add(so_doc.po_no)

		for item in so_doc.items:
			summary["metrics"]["total_ordered_qty"] += flt(item.qty)
			summary["metrics"]["total_delivered_qty"] += flt(item.delivered_qty)

		# Find Purchase Orders created against this Sales Order
		linked_pos = frappe.get_all(
			"Purchase Order Item",
			filters={"sales_order": so_name, "docstatus": ["!=", 2]},
			fields=["parent"],
			distinct=True,
		)
		for p in linked_pos:
			po_names.add(p.parent)

		# Find Delivery Notes
		linked_dns = frappe.get_all(
			"Delivery Note Item",
			filters={"against_sales_order": so_name, "docstatus": ["!=", 2]},
			fields=["parent"],
			distinct=True,
		)
		for d in linked_dns:
			dn_names.add(d.parent)

		# Find Sales Invoices
		linked_sinvs = frappe.get_all(
			"Sales Invoice Item",
			filters={"sales_order": so_name, "docstatus": ["!=", 2]},
			fields=["parent"],
			distinct=True,
		)
		for s in linked_sinvs:
			sinv_names.add(s.parent)

	# Process Purchase Orders
	pr_names = set()
	for po_name in list(po_names):
		po_doc = frappe.get_doc("Purchase Order", po_name)
		summary["purchase_orders"].append({
			"name": po_doc.name,
			"supplier": po_doc.supplier,
			"supplier_name": getattr(po_doc, "supplier_name", po_doc.supplier),
			"status": po_doc.status,
			"transaction_date": po_doc.transaction_date,
			"grand_total": po_doc.grand_total,
			"total_qty": sum(flt(i.qty) for i in po_doc.items),
			"received_qty": sum(flt(i.received_qty) for i in po_doc.items),
		})
		for item in po_doc.items:
			summary["metrics"]["total_purchased_qty"] += flt(item.qty)

		# Find Purchase Receipts
		linked_prs = frappe.get_all(
			"Purchase Receipt Item",
			filters={"purchase_order": po_name, "docstatus": ["!=", 2]},
			fields=["parent"],
			distinct=True,
		)
		for pr in linked_prs:
			pr_names.add(pr.parent)

	# Process Purchase Receipts
	for pr_name in list(pr_names):
		pr_doc = frappe.get_doc("Purchase Receipt", pr_name)
		summary["purchase_receipts"].append({
			"name": pr_doc.name,
			"supplier": pr_doc.supplier,
			"status": pr_doc.status,
			"posting_date": pr_doc.posting_date,
			"total_qty": sum(flt(i.qty) for i in pr_doc.items),
		})
		for item in pr_doc.items:
			summary["metrics"]["total_received_qty"] += flt(item.qty)

	# Process Delivery Notes
	for dn_name in list(dn_names):
		dn_doc = frappe.get_doc("Delivery Note", dn_name)
		summary["delivery_notes"].append({
			"name": dn_doc.name,
			"status": dn_doc.status,
			"posting_date": dn_doc.posting_date,
			"grand_total": dn_doc.grand_total,
			"total_qty": sum(flt(i.qty) for i in dn_doc.items),
		})

	# Process Sales Invoices
	for sinv_name in list(sinv_names):
		sinv_doc = frappe.get_doc("Sales Invoice", sinv_name)
		summary["sales_invoices"].append({
			"name": sinv_doc.name,
			"status": sinv_doc.status,
			"posting_date": sinv_doc.posting_date,
			"grand_total": sinv_doc.grand_total,
			"outstanding_amount": sinv_doc.outstanding_amount,
			"total_qty": sum(flt(i.qty) for i in sinv_doc.items),
		})
		summary["metrics"]["total_invoiced_amount"] += flt(sinv_doc.grand_total)
		for item in sinv_doc.items:
			summary["metrics"]["total_invoiced_qty"] += flt(item.qty)

		# Find Payment Entries against Sales Invoice
		payments = frappe.get_all(
			"Payment Entry Reference",
			filters={"reference_doctype": "Sales Invoice", "reference_name": sinv_name, "docstatus": 1},
			fields=["parent", "allocated_amount"],
		)
		for p in payments:
			summary["payments"].append({
				"name": p.parent,
				"allocated_amount": p.allocated_amount,
				"against": sinv_name,
			})
			summary["metrics"]["total_paid_amount"] += flt(p.allocated_amount)

	summary["customer_pos"] = list(customer_pos)

	# Build Stages State Map
	stages = summary["stages"]

	# 1. Enquiry
	if summary["enquiry"]:
		stages["enquiry"]["status"] = "green"
		stages["enquiry"]["count"] = 1
		stages["enquiry"]["docs"] = [summary["enquiry"]]
	else:
		stages["enquiry"]["status"] = "gray"

	# 2. Quotation
	q_count = len(summary["quotations"])
	stages["quotation"]["count"] = q_count
	stages["quotation"]["docs"] = summary["quotations"]
	if q_count > 0:
		has_submitted = any(q["status"] in ["Ordered", "Submitted", "Accepted"] for q in summary["quotations"])
		stages["quotation"]["status"] = "green" if has_submitted else "blue"
	elif doctype == "Quotation":
		stages["quotation"]["status"] = "blue"

	# 3. Customer PO
	po_count = len(summary["customer_pos"])
	stages["customer_po"]["count"] = po_count
	stages["customer_po"]["docs"] = [{"name": p} for p in summary["customer_pos"]]
	if po_count > 0:
		stages["customer_po"]["status"] = "green"
	elif q_count > 0:
		stages["customer_po"]["status"] = "orange"

	# 4. Sales Orders
	so_count = len(summary["sales_orders"])
	stages["sales_order"]["count"] = so_count
	stages["sales_order"]["docs"] = summary["sales_orders"]
	if so_count > 0:
		all_completed = all(s["status"] == "Completed" for s in summary["sales_orders"])
		has_draft = any(s["status"] == "Draft" for s in summary["sales_orders"])
		if all_completed:
			stages["sales_order"]["status"] = "green"
		elif has_draft:
			stages["sales_order"]["status"] = "orange"
		else:
			stages["sales_order"]["status"] = "blue"
	elif doctype == "Sales Order":
		stages["sales_order"]["status"] = "blue"

	# 5. Procurement
	po_cnt = len(summary["purchase_orders"])
	stages["procurement"]["count"] = po_cnt
	stages["procurement"]["docs"] = summary["purchase_orders"]
	if po_cnt > 0:
		all_rcvd = all(p["status"] in ["Received", "Completed"] or p["received_qty"] >= p["total_qty"] for p in summary["purchase_orders"])
		stages["procurement"]["status"] = "green" if all_rcvd else "blue"
	else:
		# Check if procurement is required
		if so_count > 0 and summary["metrics"]["total_purchased_qty"] < summary["metrics"]["total_ordered_qty"]:
			stages["procurement"]["status"] = "orange"

	# 6. Goods Receipt
	pr_cnt = len(summary["purchase_receipts"])
	stages["receipt"]["count"] = pr_cnt
	stages["receipt"]["docs"] = summary["purchase_receipts"]
	if pr_cnt > 0:
		if summary["metrics"]["total_received_qty"] >= summary["metrics"]["total_purchased_qty"] > 0:
			stages["receipt"]["status"] = "green"
		else:
			stages["receipt"]["status"] = "orange"
	elif po_cnt > 0:
		stages["receipt"]["status"] = "orange"

	# 7. Customer Delivery
	dn_cnt = len(summary["delivery_notes"])
	stages["delivery"]["count"] = dn_cnt
	stages["delivery"]["docs"] = summary["delivery_notes"]
	if dn_cnt > 0:
		if summary["metrics"]["total_delivered_qty"] >= summary["metrics"]["total_ordered_qty"] > 0:
			stages["delivery"]["status"] = "green"
		else:
			stages["delivery"]["status"] = "orange"
	elif so_count > 0:
		stages["delivery"]["status"] = "gray"

	# 8. Customer Invoice
	inv_cnt = len(summary["sales_invoices"])
	stages["invoice"]["count"] = inv_cnt
	stages["invoice"]["docs"] = summary["sales_invoices"]
	if inv_cnt > 0:
		all_paid = all(i["outstanding_amount"] <= 0 for i in summary["sales_invoices"])
		if all_paid:
			stages["invoice"]["status"] = "green"
		else:
			stages["invoice"]["status"] = "blue"
	elif dn_cnt > 0:
		stages["invoice"]["status"] = "orange"

	# 9. Payment
	pay_cnt = len(summary["payments"])
	stages["payment"]["count"] = pay_cnt
	stages["payment"]["docs"] = summary["payments"]
	if pay_cnt > 0 and summary["metrics"]["total_paid_amount"] >= summary["metrics"]["total_invoiced_amount"] > 0:
		stages["payment"]["status"] = "green"
	elif inv_cnt > 0:
		stages["payment"]["status"] = "orange"

	return summary


@frappe.whitelist()
def get_item_quantity_breakdown(doctype: str, name: str) -> list[dict]:
	"""
	Returns item-by-item quantity tracking across all phases:
	Quoted, Customer PO, Sales Ordered, Stock Available (Bin), Is Stock Item,
	Purchased, Received, Delivered, Invoiced, Paid, Pending.
	"""
	if not frappe.has_permission(doctype, "read", doc=name):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	summary = get_workflow_summary(doctype, name)
	items_map = {}

	# 1. Quoted Items
	for q in summary["quotations"]:
		q_doc = frappe.get_doc("Quotation", q["name"])
		for item in q_doc.items:
			code = item.item_code
			if code not in items_map:
				items_map[code] = _init_item_dict(code, item.item_name, item.description, item.uom, q_doc.company)
			items_map[code]["quoted_qty"] += flt(item.qty)

	# 2. Sales Order Items
	for so in summary["sales_orders"]:
		so_doc = frappe.get_doc("Sales Order", so["name"])
		for item in so_doc.items:
			code = item.item_code
			if code not in items_map:
				items_map[code] = _init_item_dict(code, item.item_name, item.description, item.uom, so_doc.company)
			items_map[code]["sales_ordered_qty"] += flt(item.qty)
			items_map[code]["delivered_qty"] += flt(item.delivered_qty)
			items_map[code]["invoiced_qty"] += flt(item.billed_amt) / (flt(item.rate) or 1.0) if flt(item.rate) > 0 else 0.0

	# 3. Purchase Order Items
	for po in summary["purchase_orders"]:
		po_doc = frappe.get_doc("Purchase Order", po["name"])
		for item in po_doc.items:
			code = item.item_code
			if code in items_map:
				items_map[code]["purchased_qty"] += flt(item.qty)
				items_map[code]["received_qty"] += flt(item.received_qty)

	# Calculate pending balances and stock statuses
	result = []
	for code, data in items_map.items():
		# Customer PO qty is considered Sales Ordered if confirmed
		data["customer_po_qty"] = max(data["sales_ordered_qty"], data["quoted_qty"] if summary["customer_pos"] else data["sales_ordered_qty"])

		# Stock availability check
		if data["is_stock_item"]:
			data["stock_available"] = _get_stock_available_qty(code, data.get("company"))
			data["stock_status"] = "available" if data["stock_available"] >= data["sales_ordered_qty"] else "shortage"
		else:
			data["stock_available"] = 0.0
			data["stock_status"] = "non_stock"

		# Pendings
		data["pending_customer_po"] = max(0.0, data["quoted_qty"] - data["customer_po_qty"])
		data["pending_purchase"] = max(0.0, data["sales_ordered_qty"] - data["purchased_qty"]) if not data["is_stock_item"] or data["stock_status"] == "shortage" else 0.0
		data["pending_receipt"] = max(0.0, data["purchased_qty"] - data["received_qty"])
		data["pending_delivery"] = max(0.0, data["sales_ordered_qty"] - data["delivered_qty"])
		data["pending_invoice"] = max(0.0, data["delivered_qty"] - data["invoiced_qty"])

		result.append(data)

	return result


def _init_item_dict(item_code: str, item_name: str, description: str, uom: str, company: str | None = None) -> dict:
	item_doc = frappe.get_cached_value("Item", item_code, ["is_stock_item", "item_group", "stock_uom"], as_dict=True) or {}
	return {
		"item_code": item_code,
		"item_name": item_name or item_code,
		"description": description or "",
		"uom": uom or item_doc.get("stock_uom", ""),
		"company": company,
		"is_stock_item": cint(item_doc.get("is_stock_item", 0)),
		"quoted_qty": 0.0,
		"customer_po_qty": 0.0,
		"sales_ordered_qty": 0.0,
		"purchased_qty": 0.0,
		"received_qty": 0.0,
		"delivered_qty": 0.0,
		"invoiced_qty": 0.0,
		"paid_qty": 0.0,
		"stock_available": 0.0,
		"stock_status": "unknown",
	}


def _get_stock_available_qty(item_code: str, company: str | None = None) -> float:
	if company:
		res = frappe.db.sql("""
			SELECT SUM(b.actual_qty) as actual_qty
			FROM `tabBin` b
			JOIN `tabWarehouse` w ON w.name = b.warehouse
			WHERE b.item_code = %s AND w.company = %s AND w.is_group = 0
		""", (item_code, company), as_dict=True)
	else:
		res = frappe.db.sql("""
			SELECT SUM(actual_qty) as actual_qty
			FROM `tabBin`
			WHERE item_code = %s
		""", (item_code,), as_dict=True)

	if res and res[0].actual_qty:
		return flt(res[0].actual_qty)
	return 0.0


@frappe.whitelist()
def get_quotation_sales_orders(quotation: str) -> dict:
	"""
	Returns all Sales Orders generated from a Quotation, and item-by-item
	quoted vs already ordered vs remaining quantities for the allocation UI.
	"""
	if not frappe.has_permission("Quotation", "read", doc=quotation):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	q_doc = frappe.get_doc("Quotation", quotation)
	items = []

	for q_item in q_doc.items:
		# Calculate already ordered qty from submitted/draft SOs
		ordered_records = frappe.db.sql("""
			SELECT SUM(so_item.qty) as ordered_qty
			FROM `tabSales Order Item` so_item
			JOIN `tabSales Order` so ON so.name = so_item.parent
			WHERE so_item.quotation_item = %s AND so.docstatus != 2
		""", (q_item.name,), as_dict=True)

		already_ordered = flt(ordered_records[0].ordered_qty) if ordered_records and ordered_records[0].ordered_qty else 0.0
		remaining = max(0.0, flt(q_item.qty) - already_ordered)

		items.append({
			"quotation_item": q_item.name,
			"item_code": q_item.item_code,
			"item_name": q_item.item_name,
			"description": q_item.description,
			"uom": q_item.uom,
			"rate": q_item.rate,
			"amount": q_item.amount,
			"quoted_qty": flt(q_item.qty),
			"already_ordered_qty": already_ordered,
			"remaining_qty": remaining,
			"allocate_qty": remaining,  # Default allocation to full remaining
		})

	# Get list of Sales Orders created from this quotation
	so_names = frappe.db.sql_list("""
		SELECT DISTINCT so_item.parent
		FROM `tabSales Order Item` so_item
		JOIN `tabSales Order` so ON so.name = so_item.parent
		WHERE so_item.prevdoc_docname = %s AND so.docstatus != 2
		ORDER BY so.creation DESC
	""", (quotation,))

	sales_orders = []
	for name in so_names:
		so = frappe.get_doc("Sales Order", name)
		sales_orders.append({
			"name": so.name,
			"status": so.status,
			"docstatus": so.docstatus,
			"transaction_date": so.transaction_date,
			"customer_po_no": so.po_no,
			"grand_total": so.grand_total,
			"items_count": len(so.items),
			"total_qty": sum(flt(i.qty) for i in so.items),
		})

	return {
		"quotation": quotation,
		"customer": q_doc.party_name if q_doc.quotation_to == "Customer" else q_doc.customer_name,
		"customer_name": q_doc.customer_name,
		"status": q_doc.status,
		"items": items,
		"sales_orders": sales_orders,
		"total_quoted_qty": sum(i["quoted_qty"] for i in items),
		"total_ordered_qty": sum(i["already_ordered_qty"] for i in items),
		"total_remaining_qty": sum(i["remaining_qty"] for i in items),
	}


@frappe.whitelist()
def create_partial_sales_order(quotation: str, items_allocation: str | list, customer_po_no: str | None = None) -> str:
	"""
	Authoritatively creates a draft Sales Order from a Quotation with specific allocated quantities.
	Uses get_mapped_doc for standard pricing, tax, and address mapping.
	"""
	if not frappe.has_permission("Sales Order", "create"):
		frappe.throw(_("Not permitted to create Sales Order"), frappe.PermissionError)

	if isinstance(items_allocation, str):
		items_allocation = json.loads(items_allocation)

	# Filter only items with allocate_qty > 0
	allocation_map = {d["quotation_item"]: flt(d.get("allocate_qty", 0)) for d in items_allocation if flt(d.get("allocate_qty", 0)) > 0}

	if not allocation_map:
		frappe.throw(_("Please specify a quantity greater than 0 for at least one item."))

	from haloerp.selling.doctype.quotation.mapper import _make_sales_order

	# Map document using standard mapper
	sales_order = _make_sales_order(quotation)
	if not getattr(sales_order, "delivery_date", None):
		sales_order.delivery_date = add_days(nowdate(), 7)

	# Adjust item rows and quantities to match exact user allocation
	valid_items = []
	for item in sales_order.items:
		q_item_id = getattr(item, "quotation_item", None)
		if q_item_id in allocation_map:
			alloc_qty = allocation_map[q_item_id]
			item.qty = alloc_qty
			item.stock_qty = alloc_qty * (flt(item.conversion_factor) or 1.0)
			item.amount = item.qty * item.rate
			if not getattr(item, "delivery_date", None):
				item.delivery_date = sales_order.delivery_date
			valid_items.append(item)

	sales_order.items = valid_items
	if customer_po_no:
		sales_order.po_no = customer_po_no

	sales_order.flags.ignore_permissions = 1
	sales_order.run_method("set_missing_values")
	sales_order.run_method("calculate_taxes_and_totals")
	sales_order.insert()

	return sales_order.name


@frappe.whitelist()
def create_multi_supplier_purchase_orders(sales_order: str, supplier_allocation: str | list) -> list[str]:
	"""
	Authoritatively splits items from a Sales Order across multiple suppliers and generates
	real draft Purchase Orders.
	Allocation format:
	[
	  {"supplier": "Supplier A", "items": [{"item_code": "ITEM-A", "sales_order_item": "...", "qty": 5, "rate": 100}]},
	  {"supplier": "Supplier B", "items": [{"item_code": "ITEM-B", "sales_order_item": "...", "qty": 10, "rate": 150}]}
	]
	"""
	if not frappe.has_permission("Purchase Order", "create"):
		frappe.throw(_("Not permitted to create Purchase Order"), frappe.PermissionError)

	if isinstance(supplier_allocation, str):
		supplier_allocation = json.loads(supplier_allocation)

	so_doc = frappe.get_doc("Sales Order", sales_order)
	created_pos = []

	for alloc in supplier_allocation:
		supplier = alloc.get("supplier")
		items = alloc.get("items", [])
		if not supplier or not items:
			continue

		po = frappe.new_doc("Purchase Order")
		po.supplier = supplier
		po.company = so_doc.company
		po.transaction_date = nowdate()
		po.schedule_date = so_doc.delivery_date or nowdate()

		for itm in items:
			qty = flt(itm.get("qty", 0))
			if qty <= 0:
				continue

			so_item = next((i for i in so_doc.items if i.name == itm.get("sales_order_item") or i.item_code == itm.get("item_code")), None)
			rate = flt(itm.get("rate")) or (so_item.rate if so_item else 0.0)

			po.append("items", {
				"item_code": itm.get("item_code"),
				"item_name": so_item.item_name if so_item else itm.get("item_code"),
				"description": so_item.description if so_item else "",
				"qty": qty,
				"rate": rate,
				"amount": qty * rate,
				"uom": so_item.uom if so_item else "Nos",
				"stock_uom": so_item.stock_uom if so_item else "Nos",
				"conversion_factor": so_item.conversion_factor if so_item else 1.0,
				"stock_qty": qty * (so_item.conversion_factor if so_item else 1.0),
				"schedule_date": so_doc.delivery_date or nowdate(),
				"sales_order": so_doc.name,
				"sales_order_item": so_item.name if so_item else None,
				"warehouse": so_item.warehouse if so_item else None,
			})

		if not po.items:
			continue

		po.flags.ignore_permissions = 1
		po.run_method("set_missing_values")
		po.run_method("calculate_taxes_and_totals")
		po.insert()
		created_pos.append(po.name)

	return created_pos


@frappe.whitelist()
def get_pending_fulfillment_overview(filters: str | dict | None = None) -> dict:
	"""
	Returns global operational cockpit metrics and filtered table records for
	the 'Pending Fulfillment' and 'Action Center' tabs.
	"""
	if isinstance(filters, str):
		filters = json.loads(filters)
	filters = filters or {}

	company = filters.get("company") or frappe.defaults.get_user_default("company")

	# 1. Sales Orders requiring procurement (submitted SOs with items where ordered_qty < stock_qty)
	so_requiring_procurement = frappe.db.sql("""
		SELECT DISTINCT so.name, so.customer, so.customer_name, so.transaction_date, so.grand_total, so.status
		FROM `tabSales Order` so
		JOIN `tabSales Order Item` soi ON soi.parent = so.name
		WHERE so.docstatus = 1 AND so.status NOT IN ('Completed', 'Closed', 'Cancelled')
		AND soi.ordered_qty < soi.stock_qty
		ORDER BY so.transaction_date DESC
		LIMIT 50
	""", as_dict=True)

	# 2. Purchase Orders pending receipt
	pos_pending_receipt = frappe.db.sql("""
		SELECT po.name, po.supplier, po.supplier_name, po.transaction_date, po.grand_total, po.status,
			   SUM(poi.qty) as total_qty, SUM(poi.received_qty) as received_qty
		FROM `tabPurchase Order` po
		JOIN `tabPurchase Order Item` poi ON poi.parent = po.name
		WHERE po.docstatus = 1 AND po.status NOT IN ('Completed', 'Closed', 'Cancelled')
		AND poi.received_qty < poi.qty
		GROUP BY po.name
		ORDER BY po.transaction_date DESC
		LIMIT 50
	""", as_dict=True)

	# 3. Sales Orders ready for delivery (stock available or items not delivered)
	so_ready_for_delivery = frappe.db.sql("""
		SELECT so.name, so.customer, so.customer_name, so.transaction_date, so.grand_total, so.status,
			   SUM(soi.qty) as total_qty, SUM(soi.delivered_qty) as delivered_qty
		FROM `tabSales Order` so
		JOIN `tabSales Order Item` soi ON soi.parent = so.name
		WHERE so.docstatus = 1 AND so.status NOT IN ('Completed', 'Closed', 'Cancelled')
		AND soi.delivered_qty < soi.qty
		GROUP BY so.name
		ORDER BY so.transaction_date DESC
		LIMIT 50
	""", as_dict=True)

	# 4. Deliveries ready for invoicing
	deliveries_pending_invoice = frappe.db.sql("""
		SELECT dn.name, dn.customer, dn.customer_name, dn.posting_date, dn.grand_total, dn.status,
			   SUM(dni.qty) as total_qty, SUM(dni.billed_amt) as billed_amt
		FROM `tabDelivery Note` dn
		JOIN `tabDelivery Note Item` dni ON dni.parent = dn.name
		WHERE dn.docstatus = 1 AND dn.status NOT IN ('Completed', 'Closed', 'Cancelled')
		AND dn.per_billed < 100
		GROUP BY dn.name
		ORDER BY dn.posting_date DESC
		LIMIT 50
	""", as_dict=True)

	# 5. Invoices with outstanding payments
	invoices_outstanding = frappe.db.sql("""
		SELECT si.name, si.customer, si.customer_name, si.posting_date, si.due_date,
			   si.grand_total, si.outstanding_amount, si.status
		FROM `tabSales Invoice` si
		WHERE si.docstatus = 1 AND si.outstanding_amount > 0
		ORDER BY si.due_date ASC
		LIMIT 50
	""", as_dict=True)

	return {
		"counts": {
			"procurement_required": len(so_requiring_procurement),
			"pending_receipts": len(pos_pending_receipt),
			"ready_for_delivery": len(so_ready_for_delivery),
			"pending_invoices": len(deliveries_pending_invoice),
			"outstanding_invoices": len(invoices_outstanding),
		},
		"so_requiring_procurement": so_requiring_procurement,
		"pos_pending_receipt": pos_pending_receipt,
		"so_ready_for_delivery": so_ready_for_delivery,
		"deliveries_pending_invoice": deliveries_pending_invoice,
		"invoices_outstanding": invoices_outstanding,
	}


@frappe.whitelist()
def get_traceability_graph(doctype: str, name: str) -> dict:
	"""
	Returns nodes and edges representing the entire hierarchical document tree.
	"""
	summary = get_workflow_summary(doctype, name)
	nodes = []
	edges = []

	# Root node
	nodes.append({
		"id": f"{doctype}:{name}",
		"label": f"{doctype} {name}",
		"doctype": doctype,
		"name": name,
		"type": "root",
		"status": summary["status"],
	})

	# Quotation nodes
	for q in summary["quotations"]:
		q_id = f"Quotation:{q['name']}"
		if q_id != f"{doctype}:{name}":
			nodes.append({"id": q_id, "label": f"Quotation {q['name']}", "doctype": "Quotation", "name": q["name"], "status": q["status"]})
			edges.append({"source": f"{doctype}:{name}", "target": q_id, "label": "Quoted"})

	# Sales Order nodes
	for so in summary["sales_orders"]:
		so_id = f"Sales Order:{so['name']}"
		nodes.append({"id": so_id, "label": f"SO {so['name']}", "doctype": "Sales Order", "name": so["name"], "status": so["status"]})
		source = f"Quotation:{summary['quotations'][0]['name']}" if summary["quotations"] else f"{doctype}:{name}"
		edges.append({"source": source, "target": so_id, "label": "Ordered"})

		# Purchase Orders linked to this SO
		for po in summary["purchase_orders"]:
			po_id = f"Purchase Order:{po['name']}"
			if not any(n["id"] == po_id for n in nodes):
				nodes.append({"id": po_id, "label": f"PO {po['name']} ({po['supplier']})", "doctype": "Purchase Order", "name": po["name"], "status": po["status"]})
			edges.append({"source": so_id, "target": po_id, "label": "Procured"})

		# Delivery Notes linked to this SO
		for dn in summary["delivery_notes"]:
			dn_id = f"Delivery Note:{dn['name']}"
			if not any(n["id"] == dn_id for n in nodes):
				nodes.append({"id": dn_id, "label": f"DN {dn['name']}", "doctype": "Delivery Note", "name": dn["name"], "status": dn["status"]})
			edges.append({"source": so_id, "target": dn_id, "label": "Delivered"})

	# Purchase Receipts
	for pr in summary["purchase_receipts"]:
		pr_id = f"Purchase Receipt:{pr['name']}"
		nodes.append({"id": pr_id, "label": f"GRN {pr['name']}", "doctype": "Purchase Receipt", "name": pr["name"], "status": pr["status"]})
		if summary["purchase_orders"]:
			edges.append({"source": f"Purchase Order:{summary['purchase_orders'][0]['name']}", "target": pr_id, "label": "Received"})

	# Sales Invoices
	for sinv in summary["sales_invoices"]:
		sinv_id = f"Sales Invoice:{sinv['name']}"
		nodes.append({"id": sinv_id, "label": f"Invoice {sinv['name']}", "doctype": "Sales Invoice", "name": sinv["name"], "status": sinv["status"]})
		source = f"Delivery Note:{summary['delivery_notes'][0]['name']}" if summary["delivery_notes"] else (f"Sales Order:{summary['sales_orders'][0]['name']}" if summary["sales_orders"] else f"{doctype}:{name}")
		edges.append({"source": source, "target": sinv_id, "label": "Invoiced"})

		# Payment Entries
		for pay in summary["payments"]:
			pay_id = f"Payment Entry:{pay['name']}"
			if not any(n["id"] == pay_id for n in nodes):
				nodes.append({"id": pay_id, "label": f"Payment {pay['name']}", "doctype": "Payment Entry", "name": pay["name"], "status": "Submitted"})
			edges.append({"source": sinv_id, "target": pay_id, "label": "Paid"})

	return {"nodes": nodes, "edges": edges}
