/* HaloAllocationDialogs — Partial Sales Order & Multi-Supplier Purchase Order Allocation */

frappe.provide("haloerp.workflow");

haloerp.workflow.HaloSalesOrderAllocationDialog = class HaloSalesOrderAllocationDialog {
	constructor(quotation_name) {
		this.quotation_name = quotation_name;
		this.dialog = null;
		this.data = null;
		this.init();
	}

	init() {
		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.get_quotation_sales_orders",
			args: { quotation: this.quotation_name },
			callback: (r) => {
				if (r.message) {
					this.data = r.message;
					this.render();
				}
			},
		});
	}

	render() {
		const items = this.data.items || [];
		if (!items.length) {
			frappe.msgprint(__("No items found in Quotation"));
			return;
		}

		let table_rows = "";
		items.forEach((item, idx) => {
			table_rows += `
				<tr data-row-idx="${idx}" data-item="${item.quotation_item}">
					<td><b>${item.item_code}</b><br><small class="text-muted">${item.item_name || ""}</small></td>
					<td class="text-right">${item.quoted_qty} ${item.uom}</td>
					<td class="text-right">${item.already_ordered_qty}</td>
					<td class="text-center">
						<input type="number" class="halo-alloc-input alloc-qty-input"
							value="${item.remaining_qty}"
							min="0"
							max="${item.remaining_qty}"
							data-item="${item.quotation_item}"
							data-quoted="${item.quoted_qty}"
							data-ordered="${item.already_ordered_qty}">
					</td>
					<td class="text-right remaining-qty-col">${item.remaining_qty - item.remaining_qty}</td>
				</tr>
			`;
		});

		const body_html = `
			<div class="halo-alloc-wrapper p-2">
				<div class="d-flex justify-content-between align-items-center mb-3">
					<div>
						<h5 class="mb-0" style="color: #1769e0; font-weight: 700;">${__("Create Sales Order from Quotation")}</h5>
						<small class="text-muted">${__("Quotation")}: <b>${this.quotation_name}</b> | ${__("Customer")}: <b>${this.data.customer_name || this.data.customer}</b></small>
					</div>
					<div class="form-group mb-0" style="min-width: 200px;">
						<label class="control-label" style="font-size: 11px;">${__("Customer Purchase Order #")}</label>
						<input type="text" class="form-control input-sm customer-po-input" placeholder="e.g. PO-2026-001">
					</div>
				</div>

				<div class="table-responsive border rounded mb-3">
					<table class="halo-allocation-table">
						<thead>
							<tr>
								<th>${__("Item")}</th>
								<th class="text-right">${__("Quoted")}</th>
								<th class="text-right">${__("Already Ordered")}</th>
								<th class="text-center" style="width: 120px;">${__("This Sales Order")}</th>
								<th class="text-right">${__("Remaining")}</th>
							</tr>
						</thead>
						<tbody>
							${table_rows}
						</tbody>
					</table>
				</div>

				<div class="d-flex justify-content-between alert alert-info mb-0" style="font-size: 12px; padding: 8px 14px;">
					<span>${__("Total Quoted")}: <b id="alloc-total-quoted">${this.data.total_quoted_qty}</b></span>
					<span>${__("Already Ordered")}: <b id="alloc-total-ordered">${this.data.total_ordered_qty}</b></span>
					<span>${__("This Order")}: <b id="alloc-total-this-order">${this.data.total_remaining_qty}</b></span>
				</div>
			</div>
		`;

		this.dialog = new frappe.ui.Dialog({
			title: __("Item Allocation for Sales Order"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "alloc_html",
					options: body_html,
				},
			],
			size: "large",
			primary_action_label: __("Create Sales Order"),
			primary_action: () => this.submit(),
		});

		this.dialog.show();

		// Bind recalculation
		this.dialog.$wrapper.find(".alloc-qty-input").on("input change", (e) => {
			const $input = $(e.target);
			const row = $input.closest("tr");
			const quoted = flt($input.data("quoted"));
			const ordered = flt($input.data("ordered"));
			const alloc = flt($input.val());

			const remaining = Math.max(0, quoted - ordered - alloc);
			row.find(".remaining-qty-col").text(remaining);

			// Recalculate total this order
			let total_this = 0;
			this.dialog.$wrapper.find(".alloc-qty-input").each(function () {
				total_this += flt($(this).val());
			});
			this.dialog.$wrapper.find("#alloc-total-this-order").text(total_this);
		});
	}

	submit() {
		const allocations = [];
		this.dialog.$wrapper.find(".alloc-qty-input").each(function () {
			const item_id = $(this).data("item");
			const qty = flt($(this).val());
			if (qty > 0) {
				allocations.push({
					quotation_item: item_id,
					allocate_qty: qty,
				});
			}
		});

		if (!allocations.length) {
			frappe.msgprint(__("Please enter a quantity greater than 0 for at least one item."));
			return;
		}

		const po_no = this.dialog.$wrapper.find(".customer-po-input").val();

		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.create_partial_sales_order",
			args: {
				quotation: this.quotation_name,
				items_allocation: allocations,
				customer_po_no: po_no,
			},
			freeze: true,
			freeze_message: __("Creating Sales Order..."),
			callback: (r) => {
				if (r.message) {
					this.dialog.hide();
					frappe.show_alert({
						message: __("Sales Order {0} created successfully", [r.message]),
						indicator: "green",
					});
					frappe.set_route("Form", "Sales Order", r.message);
				}
			},
		});
	}
};


haloerp.workflow.HaloPurchaseAllocationDialog = class HaloPurchaseAllocationDialog {
	constructor(sales_order_name) {
		this.sales_order_name = sales_order_name;
		this.dialog = null;
		this.init();
	}

	init() {
		frappe.model.with_doc("Sales Order", this.sales_order_name, () => {
			this.so_doc = frappe.get_doc("Sales Order", this.sales_order_name);
			this.render();
		});
	}

	render() {
		const items = this.so_doc.items || [];
		if (!items.length) {
			frappe.msgprint(__("No items found in Sales Order"));
			return;
		}

		let table_rows = "";
		items.forEach((item, idx) => {
			table_rows += `
				<tr data-row-idx="${idx}" data-item="${item.name}">
					<td>
						<b>${item.item_code}</b><br>
						<small class="text-muted">${item.item_name || ""}</small>
					</td>
					<td class="text-right">${item.qty} ${item.uom}</td>
					<td class="text-right">${item.ordered_qty || 0}</td>
					<td>
						<input type="text" class="form-control input-sm supplier-autocomplete"
							data-item="${item.name}"
							placeholder="${__("Select Supplier...")}">
					</td>
					<td class="text-center">
						<input type="number" class="halo-alloc-input po-qty-input"
							value="${Math.max(0, item.qty - (item.ordered_qty || 0))}"
							min="0"
							max="${item.qty}">
					</td>
				</tr>
			`;
		});

		const body_html = `
			<div class="p-2">
				<div class="mb-3">
					<h5 class="mb-0" style="color: #1769e0; font-weight: 700;">${__("Multi-Supplier Purchase Order Allocation")}</h5>
					<small class="text-muted">${__("Sales Order")}: <b>${this.sales_order_name}</b> | ${__("Customer")}: <b>${this.so_doc.customer_name || this.so_doc.customer}</b></small>
				</div>

				<div class="table-responsive border rounded mb-3">
					<table class="halo-allocation-table">
						<thead>
							<tr>
								<th>${__("Item")}</th>
								<th class="text-right">${__("SO Qty")}</th>
								<th class="text-right">${__("Already Purchased")}</th>
								<th style="min-width: 180px;">${__("Supplier")}</th>
								<th class="text-center" style="width: 110px;">${__("PO Qty")}</th>
							</tr>
						</thead>
						<tbody>
							${table_rows}
						</tbody>
					</table>
				</div>
				<p class="text-muted" style="font-size: 11.5px;">
					<i class="fa fa-info-circle"></i> ${__("Multiple items assigned to the same supplier will be grouped into one Purchase Order.")}
				</p>
			</div>
		`;

		this.dialog = new frappe.ui.Dialog({
			title: __("Supplier Allocation for Purchase Orders"),
			fields: [
				{
					fieldtype: "HTML",
					fieldname: "alloc_html",
					options: body_html,
				},
			],
			size: "large",
			primary_action_label: __("Create Purchase Orders"),
			primary_action: () => this.submit(),
		});

		this.dialog.show();

		// Setup Awesomeplete supplier autocompletes
		frappe.db.get_link_options("Supplier", "").then((suppliers) => {
			this.dialog.$wrapper.find(".supplier-autocomplete").each(function () {
				new Awesomplete(this, {
					list: suppliers.map((s) => s.value),
					minChars: 0,
				});
			});
		});
	}

	submit() {
		const supplier_map = {};
		let has_items = false;

		const so_items = this.so_doc.items || [];

		this.dialog.$wrapper.find("tbody tr").each(function (idx) {
			const item_name = $(this).data("item");
			const supplier = $(this).find(".supplier-autocomplete").val().trim();
			const qty = flt($(this).find(".po-qty-input").val());

			const so_item = so_items.find((i) => i.name === item_name) || so_items[idx];

			if (supplier && qty > 0 && so_item) {
				has_items = true;
				if (!supplier_map[supplier]) {
					supplier_map[supplier] = { supplier: supplier, items: [] };
				}
				supplier_map[supplier].items.push({
					item_code: so_item.item_code,
					sales_order_item: so_item.name,
					qty: qty,
					rate: so_item.rate,
				});
			}
		});

		if (!has_items) {
			frappe.msgprint(__("Please select a Supplier and allocate a quantity > 0 for at least one item."));
			return;
		}

		const allocations = Object.values(supplier_map);

		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.create_multi_supplier_purchase_orders",
			args: {
				sales_order: this.sales_order_name,
				supplier_allocation: allocations,
			},
			freeze: true,
			freeze_message: __("Creating Purchase Orders..."),
			callback: (r) => {
				if (r.message && r.message.length) {
					this.dialog.hide();
					frappe.msgprint({
						title: __("Purchase Orders Created"),
						message: __("Created {0} Purchase Order(s):<br><ul>{1}</ul>", [
							r.message.length,
							r.message.map((po) => `<li><a href="/app/purchase-order/${po}"><b>${po}</b></a></li>`).join(""),
						]),
						indicator: "green",
					});
				}
			},
		});
	}
};
