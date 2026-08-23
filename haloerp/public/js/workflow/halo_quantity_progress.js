/* HaloQuantityProgress — Per-Item and Overall Quantity Breakdown */

frappe.provide("haloerp.workflow");

haloerp.workflow.HaloQuantityProgress = class HaloQuantityProgress {
	constructor(opts) {
		this.wrapper = opts.wrapper;
		this.doctype = opts.doctype;
		this.docname = opts.docname;
		this.items = opts.items || [];
		this.init();
	}

	init() {
		if (this.items.length) {
			this.render();
		} else {
			this.fetch_data();
		}
	}

	fetch_data() {
		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.get_item_quantity_breakdown",
			args: {
				doctype: this.doctype,
				name: this.docname,
			},
			callback: (r) => {
				if (r.message) {
					this.items = r.message;
					this.render();
				}
			},
		});
	}

	render() {
		if (!this.items.length) {
			this.wrapper.html(`<div class="text-muted text-center p-3">${__("No line items found")}</div>`);
			return;
		}

		let html = `<div class="halo-quantity-progress-container">`;

		this.items.forEach((item) => {
			const max_qty = Math.max(item.quoted_qty, item.sales_ordered_qty, item.purchased_qty, 1.0);

			const p_quoted = Math.min(100, (item.quoted_qty / max_qty) * 100);
			const p_ordered = Math.min(100, (item.sales_ordered_qty / max_qty) * 100);
			const p_purchased = Math.min(100, (item.purchased_qty / max_qty) * 100);
			const p_received = Math.min(100, (item.received_qty / max_qty) * 100);
			const p_delivered = Math.min(100, (item.delivered_qty / max_qty) * 100);
			const p_invoiced = Math.min(100, (item.invoiced_qty / max_qty) * 100);

			const stock_badge = item.is_stock_item
				? (item.stock_available >= item.sales_ordered_qty
					? `<span class="halo-stock-badge available"><i class="fa fa-check"></i> Stock Available (${item.stock_available} ${item.uom})</span>`
					: `<span class="halo-stock-badge procurement-required"><i class="fa fa-warning"></i> Stock Shortage (${item.stock_available} ${item.uom})</span>`)
				: `<span class="halo-stock-badge procurement-required"><i class="fa fa-refresh"></i> Non-Stock / Procurement</span>`;

			html += `
				<div class="halo-qty-progress-card">
					<div class="halo-qty-item-header">
						<div>
							<span class="halo-qty-item-title">${item.item_code}</span>
							${item.item_name && item.item_name !== item.item_code ? `<span class="text-muted ml-2">${item.item_name}</span>` : ""}
						</div>
						<div>${stock_badge}</div>
					</div>

					<div class="halo-progress-row">
						<span class="halo-progress-label">${__("Quoted")}</span>
						<div class="halo-progress-track">
							<div class="halo-progress-fill blue" style="width: ${p_quoted}%;"></div>
						</div>
						<span class="halo-progress-val">${item.quoted_qty} ${item.uom}</span>
					</div>

					<div class="halo-progress-row">
						<span class="halo-progress-label">${__("Sales Order")}</span>
						<div class="halo-progress-track">
							<div class="halo-progress-fill indigo" style="width: ${p_ordered}%;"></div>
						</div>
						<span class="halo-progress-val">${item.sales_ordered_qty} / ${item.quoted_qty}</span>
					</div>

					<div class="halo-progress-row">
						<span class="halo-progress-label">${__("Purchased")}</span>
						<div class="halo-progress-track">
							<div class="halo-progress-fill purple" style="width: ${p_purchased}%;"></div>
						</div>
						<span class="halo-progress-val">${item.purchased_qty} / ${item.sales_ordered_qty}</span>
					</div>

					<div class="halo-progress-row">
						<span class="halo-progress-label">${__("Received")}</span>
						<div class="halo-progress-track">
							<div class="halo-progress-fill orange" style="width: ${p_received}%;"></div>
						</div>
						<span class="halo-progress-val">${item.received_qty} / ${item.purchased_qty}</span>
					</div>

					<div class="halo-progress-row">
						<span class="halo-progress-label">${__("Delivered")}</span>
						<div class="halo-progress-track">
							<div class="halo-progress-fill green" style="width: ${p_delivered}%;"></div>
						</div>
						<span class="halo-progress-val">${item.delivered_qty} / ${item.sales_ordered_qty}</span>
					</div>

					<div class="halo-progress-row">
						<span class="halo-progress-label">${__("Invoiced")}</span>
						<div class="halo-progress-track">
							<div class="halo-progress-fill green" style="width: ${p_invoiced}%;"></div>
						</div>
						<span class="halo-progress-val">${item.invoiced_qty} / ${item.delivered_qty}</span>
					</div>

					<div class="d-flex justify-content-between text-muted mt-2 pt-2 border-top" style="font-size: 11px;">
						<span>${__("Pending PO")}: <b>${item.pending_purchase}</b></span>
						<span>${__("Pending Receipt")}: <b>${item.pending_receipt}</b></span>
						<span>${__("Pending Delivery")}: <b>${item.pending_delivery}</b></span>
						<span>${__("Pending Invoice")}: <b>${item.pending_invoice}</b></span>
					</div>
				</div>
			`;
		});

		html += `</div>`;
		this.wrapper.html(html);
	}
};
