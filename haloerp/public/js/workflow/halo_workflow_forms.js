/* HaloERP Form Integration — Workflow Header and Action Triggers */

$(document).on("form-refresh", (e, frm) => {
	if (!frm || !frm.doc || frm.doc.__islocal) return;

	const target_doctypes = [
		"Quotation",
		"Sales Order",
		"Purchase Order",
		"Delivery Note",
		"Sales Invoice",
		"Purchase Receipt",
	];

	if (target_doctypes.includes(frm.doctype)) {
		render_form_workflow_header(frm);
		enhance_form_actions(frm);
	}
});

function render_form_workflow_header(frm) {
	let $header_wrapper = frm.$wrapper.find(".halo-workflow-header-hook");
	if (!$header_wrapper.length) {
		$header_wrapper = $('<div class="halo-workflow-header-hook" style="padding: 10px 15px 0 15px;"></div>')
			.prependTo(frm.layout.wrapper);
	}

	new haloerp.workflow.HaloWorkflowHeader({
		wrapper: $header_wrapper,
		doctype: frm.doctype,
		docname: frm.doc.name,
		frm: frm,
	});
}

function enhance_form_actions(frm) {
	// 1. Quotation: Add "Create Partial Sales Order" button
	if (frm.doctype === "Quotation" && frm.doc.docstatus === 1) {
		frm.add_custom_button(__("Partial Sales Order"), () => {
			new haloerp.workflow.HaloSalesOrderAllocationDialog(frm.doc.name);
		}, __("Create"));

		frm.add_custom_button(__("Workflow Control Center"), () => {
			frappe.set_route("sales-procurement-center", {
				doctype: "Quotation",
				name: frm.doc.name,
			});
		});
	}

	// 2. Sales Order: Add "Multi-Supplier PO Allocation" button
	if (frm.doctype === "Sales Order" && frm.doc.docstatus === 1) {
		frm.add_custom_button(__("Multi-Supplier PO"), () => {
			new haloerp.workflow.HaloPurchaseAllocationDialog(frm.doc.name);
		}, __("Create"));

		frm.add_custom_button(__("Workflow Control Center"), () => {
			frappe.set_route("sales-procurement-center", {
				doctype: "Sales Order",
				name: frm.doc.name,
			});
		});
	}
}
