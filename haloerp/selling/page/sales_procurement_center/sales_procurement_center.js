/* HaloERP Sales & Procurement Control Center Page */

frappe.pages["sales-procurement-center"].on_page_load = function (wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __("Sales & Procurement Control Center"),
		single_column: true,
	});

	wrapper.control_center = new haloerp.SalesProcurementCenter(wrapper, page);
	frappe.breadcrumbs.add("Selling");
};

frappe.pages["sales-procurement-center"].on_page_show = function (wrapper) {
	if (wrapper.control_center) {
		const route = frappe.get_route();
		const options = frappe.route_options;
		if (options && (options.name || options.doctype || options.customer)) {
			wrapper.control_center.load_context(options);
			frappe.route_options = null;
		}
	}
};

haloerp.SalesProcurementCenter = class SalesProcurementCenter {
	constructor(wrapper, page) {
		this.wrapper = wrapper;
		this.page = page;
		this.active_tab = "workflow"; // "workflow" | "pending" | "actions"
		this.current_doc = { doctype: "Quotation", name: null };
		this.summary_data = null;
		this.init();
	}

	init() {
		this.setup_header();
		this.setup_layout();
		this.bind_events();

		// Auto load first available Quotation or Sales Order
		frappe.db.get_list("Quotation", { filters: { docstatus: ["!=", 2] }, limit: 1 }).then((res) => {
			if (res && res.length) {
				this.quotation_field.set_value(res[0].name);
			} else {
				this.load_action_center();
			}
		});
	}

	setup_header() {
		const me = this;

		// Customer link
		this.customer_field = this.page.add_field({
			fieldtype: "Link",
			fieldname: "customer",
			options: "Customer",
			label: __("Customer"),
			change: function () {
				const val = this.get_value();
				if (val) me.load_customer_data(val);
			},
		});

		// Quotation link
		this.quotation_field = this.page.add_field({
			fieldtype: "Link",
			fieldname: "quotation",
			options: "Quotation",
			label: __("Quotation"),
			change: function () {
				const val = this.get_value();
				if (val) {
					me.current_doc = { doctype: "Quotation", name: val };
					me.refresh();
				}
			},
		});

		// Sales Order link
		this.so_field = this.page.add_field({
			fieldtype: "Link",
			fieldname: "sales_order",
			options: "Sales Order",
			label: __("Sales Order"),
			change: function () {
				const val = this.get_value();
				if (val) {
					me.current_doc = { doctype: "Sales Order", name: val };
					me.refresh();
				}
			},
		});

		// Primary Refresh Action
		this.page.set_primary_action(
			__("Refresh"),
			() => this.refresh(),
			"refresh"
		);

		// Custom Tab Switcher
		this.page.add_inner_button(__("Workflow Tracker"), () => this.switch_tab("workflow"));
		this.page.add_inner_button(__("Pending Fulfillment"), () => this.switch_tab("pending"));
		this.page.add_inner_button(__("Actions Required"), () => this.switch_tab("actions"));
	}

	setup_layout() {
		this.$main = $(`
			<div class="halo-control-center-layout">
				<!-- Tab 1: Workflow Lifecycle View -->
				<div class="halo-tab-content halo-tab-workflow">
					<div class="halo-stage-header-slot"></div>
					<div class="row">
						<div class="col-md-7">
							<div class="card mb-3 p-3">
								<h6 class="card-title text-primary mb-3">
									<i class="fa fa-shopping-cart"></i> ${__("Sales Orders & Customer Delivery")}
								</h6>
								<div class="halo-so-fulfillment-slot"></div>
							</div>
							<div class="card p-3">
								<h6 class="card-title text-primary mb-3">
									<i class="fa fa-tasks"></i> ${__("Per-Item Quantity Pipeline")}
								</h6>
								<div class="halo-qty-breakdown-slot"></div>
							</div>
						</div>
						<div class="col-md-5">
							<div class="card mb-3 p-3">
								<h6 class="card-title text-primary mb-3">
									<i class="fa fa-truck"></i> ${__("Procurement & Multi-Supplier Board")}
								</h6>
								<div class="halo-procurement-board-slot"></div>
							</div>
							<div class="card p-3">
								<h6 class="card-title text-primary mb-3">
									<i class="fa fa-sitemap"></i> ${__("Document Traceability Map")}
								</h6>
								<div class="halo-traceability-slot"></div>
							</div>
						</div>
					</div>
				</div>

				<!-- Tab 2: Pending Fulfillment Center -->
				<div class="halo-tab-content halo-tab-pending" style="display: none;">
					<div class="card p-3 mb-3">
						<h5 class="mb-2 text-primary font-weight-bold">${__("Global Pending Fulfillment Center")}</h5>
						<p class="text-muted small">${__("Complete multi-document operational matrix with real-time pending quantities.")}</p>
						<div class="halo-pending-fulfillment-slot"></div>
					</div>
				</div>

				<!-- Tab 3: Actions Required Cockpit -->
				<div class="halo-tab-content halo-tab-actions" style="display: none;">
					<div class="halo-action-cockpit-slot"></div>
				</div>
			</div>
		`).appendTo(this.page.main);
	}

	bind_events() {
		// Event delegation for action triggers
		this.$main.on("click", ".btn-create-partial-so", (e) => {
			const q = $(e.currentTarget).data("quotation") || this.quotation_field.get_value();
			if (q) new haloerp.workflow.HaloSalesOrderAllocationDialog(q);
		});

		this.$main.on("click", ".btn-create-multi-po", (e) => {
			const so = $(e.currentTarget).data("so") || this.so_field.get_value();
			if (so) new haloerp.workflow.HaloPurchaseAllocationDialog(so);
		});
	}

	load_context(opts) {
		if (opts.doctype && opts.name) {
			this.current_doc = { doctype: opts.doctype, name: opts.name };
			if (opts.doctype === "Quotation") this.quotation_field.set_value(opts.name);
			if (opts.doctype === "Sales Order") this.so_field.set_value(opts.name);
		}
		if (opts.customer) {
			this.customer_field.set_value(opts.customer);
		}
		this.refresh();
	}

	switch_tab(tab) {
		this.active_tab = tab;
		this.$main.find(".halo-tab-content").hide();
		this.$main.find(`.halo-tab-${tab}`).show();

		if (tab === "workflow") this.refresh_workflow();
		if (tab === "pending") this.load_pending_fulfillment();
		if (tab === "actions") this.load_action_center();
	}

	refresh() {
		if (this.active_tab === "workflow") this.refresh_workflow();
		else if (this.active_tab === "pending") this.load_pending_fulfillment();
		else if (this.active_tab === "actions") this.load_action_center();
	}

	refresh_workflow() {
		if (!this.current_doc.name) {
			this.$main.find(".halo-stage-header-slot").html(`
				<div class="alert alert-info">
					<i class="fa fa-info-circle"></i> ${__("Please select a Quotation, Sales Order, or Customer above to view the live workflow.")}
				</div>
			`);
			return;
		}

		// 1. Stage Header
		new haloerp.workflow.HaloWorkflowHeader({
			wrapper: this.$main.find(".halo-stage-header-slot"),
			doctype: this.current_doc.doctype,
			docname: this.current_doc.name,
		});

		// 2. Fetch full summary for operational panels
		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.get_workflow_summary",
			args: {
				doctype: this.current_doc.doctype,
				name: this.current_doc.name,
			},
			callback: (r) => {
				if (r.message) {
					this.summary_data = r.message;
					this.render_sales_orders_panel();
					this.render_procurement_board();
					this.render_traceability();
				}
			},
		});

		// 3. Item breakdown
		new haloerp.workflow.HaloQuantityProgress({
			wrapper: this.$main.find(".halo-qty-breakdown-slot"),
			doctype: this.current_doc.doctype,
			docname: this.current_doc.name,
		});
	}

	render_sales_orders_panel() {
		const sos = this.summary_data.sales_orders || [];
		let html = "";

		if (!sos.length) {
			html = `
				<div class="text-muted p-2 mb-2">${__("No Sales Orders created yet.")}</div>
				${this.summary_data.doctype === "Quotation" ? `
					<button class="btn btn-sm btn-primary btn-create-partial-so" data-quotation="${this.summary_data.name}">
						<i class="fa fa-plus"></i> ${__("Create Sales Order for Quoted Items")}
					</button>
				` : ""}
			`;
		} else {
			html = `
				<div class="table-responsive mb-2">
					<table class="table table-sm table-hover border">
						<thead class="thead-light">
							<tr>
								<th>${__("Sales Order")}</th>
								<th>${__("Customer PO")}</th>
								<th class="text-right">${__("Ordered")}</th>
								<th class="text-right">${__("Delivered")}</th>
								<th>${__("Status")}</th>
							</tr>
						</thead>
						<tbody>
			`;
			sos.forEach((so) => {
				html += `
					<tr>
						<td><a href="/app/sales-order/${so.name}"><b>${so.name}</b></a></td>
						<td>${so.po_no || "-"}</td>
						<td class="text-right">${so.total_qty}</td>
						<td class="text-right">${so.delivered_qty}</td>
						<td><span class="badge badge-info">${so.status}</span></td>
					</tr>
				`;
			});
			html += `
						</tbody>
					</table>
				</div>
				<div class="d-flex gap-2">
					${this.summary_data.doctype === "Quotation" ? `
						<button class="btn btn-xs btn-default btn-create-partial-so" data-quotation="${this.summary_data.name}">
							<i class="fa fa-plus"></i> ${__("Create Another Sales Order")}
						</button>
					` : ""}
					<a href="/app/delivery-note/new" class="btn btn-xs btn-primary ml-2">
						<i class="fa fa-truck"></i> ${__("Create Delivery Note")}
					</a>
				</div>
			`;
		}

		this.$main.find(".halo-so-fulfillment-slot").html(html);
	}

	render_procurement_board() {
		const pos = this.summary_data.purchase_orders || [];
		let html = "";

		if (!pos.length) {
			html = `
				<div class="text-muted p-2 mb-2">${__("No Purchase Orders linked to this order.")}</div>
				<button class="btn btn-sm btn-primary btn-create-multi-po" data-so="${this.current_doc.name}">
					<i class="fa fa-plus"></i> ${__("Allocate Items to Suppliers")}
				</button>
			`;
		} else {
			html = `
				<div class="table-responsive mb-2">
					<table class="table table-sm table-hover border">
						<thead class="thead-light">
							<tr>
								<th>${__("Supplier")}</th>
								<th>${__("PO")}</th>
								<th class="text-right">${__("Ordered")}</th>
								<th class="text-right">${__("Received")}</th>
								<th>${__("Status")}</th>
							</tr>
						</thead>
						<tbody>
			`;
			pos.forEach((po) => {
				html += `
					<tr>
						<td><b>${po.supplier_name || po.supplier}</b></td>
						<td><a href="/app/purchase-order/${po.name}">${po.name}</a></td>
						<td class="text-right">${po.total_qty}</td>
						<td class="text-right">${po.received_qty}</td>
						<td><span class="badge badge-warning">${po.status}</span></td>
					</tr>
				`;
			});
			html += `
						</tbody>
					</table>
				</div>
				<button class="btn btn-xs btn-default btn-create-multi-po" data-so="${this.current_doc.name}">
					<i class="fa fa-plus"></i> ${__("Allocate Additional PO")}
				</button>
			`;
		}

		this.$main.find(".halo-procurement-board-slot").html(html);
	}

	render_traceability() {
		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.get_traceability_graph",
			args: {
				doctype: this.current_doc.doctype,
				name: this.current_doc.name,
			},
			callback: (r) => {
				if (r.message && r.message.nodes) {
					let tree_html = `<div class="halo-traceability-tree">`;
					const nodes = r.message.nodes;
					nodes.forEach((node) => {
						tree_html += `
							<div class="halo-tree-row">
								<a href="/app/${frappe.router.slug(node.doctype)}/${node.name}" class="halo-tree-node">
									<i class="fa fa-file-text-o text-primary"></i>
									<span>${node.label}</span>
									<span class="badge badge-light ml-1">${node.status || "Active"}</span>
								</a>
							</div>
						`;
					});
					tree_html += `</div>`;
					this.$main.find(".halo-traceability-slot").html(tree_html);
				}
			},
		});
	}

	load_pending_fulfillment() {
		const $slot = this.$main.find(".halo-pending-fulfillment-slot");
		$slot.html(`<div class="text-center p-3 text-muted"><i class="fa fa-spinner fa-spin"></i> ${__("Loading Pending Fulfillment...")}</div>`);

		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.get_pending_fulfillment_overview",
			callback: (r) => {
				if (r.message) {
					const data = r.message;
					let html = `
						<div class="table-responsive">
							<table class="table table-bordered table-sm table-hover">
								<thead class="thead-light">
									<tr>
										<th>${__("Sales Order")}</th>
										<th>${__("Customer")}</th>
										<th>${__("Date")}</th>
										<th class="text-right">${__("Grand Total")}</th>
										<th>${__("Procurement Status")}</th>
										<th class="text-center">${__("Actions")}</th>
									</tr>
								</thead>
								<tbody>
					`;
					(data.so_requiring_procurement || []).forEach((so) => {
						html += `
							<tr>
								<td><a href="/app/sales-order/${so.name}"><b>${so.name}</b></a></td>
								<td>${so.customer_name || so.customer}</td>
								<td>${so.transaction_date}</td>
								<td class="text-right">${format_currency(so.grand_total)}</td>
								<td><span class="badge badge-warning">${__("Procurement Required")}</span></td>
								<td class="text-center">
									<button class="btn btn-xs btn-primary btn-create-multi-po" data-so="${so.name}">
										${__("Allocate PO")}
									</button>
								</td>
							</tr>
						`;
					});
					html += `
								</tbody>
							</table>
						</div>
					`;
					$slot.html(html);
				}
			},
		});
	}

	load_action_center() {
		const $slot = this.$main.find(".halo-action-cockpit-slot");
		$slot.html(`<div class="text-center p-3 text-muted"><i class="fa fa-spinner fa-spin"></i> ${__("Loading Actions...")}</div>`);

		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.get_pending_fulfillment_overview",
			callback: (r) => {
				if (r.message) {
					const c = r.message.counts;
					const html = `
						<div class="halo-action-center mb-3">
							<div class="halo-action-pill warning" data-filter="procurement">
								<i class="fa fa-exclamation-triangle text-warning"></i>
								<span>${__("Sales Orders Requiring Procurement")}</span>
								<span class="halo-pill-count">${c.procurement_required}</span>
							</div>
							<div class="halo-action-pill warning" data-filter="receipts">
								<i class="fa fa-clock-o text-warning"></i>
								<span>${__("POs Pending Goods Receipt")}</span>
								<span class="halo-pill-count">${c.pending_receipts}</span>
							</div>
							<div class="halo-action-pill" data-filter="delivery">
								<i class="fa fa-paper-plane text-primary"></i>
								<span>${__("Orders Ready for Delivery")}</span>
								<span class="halo-pill-count">${c.ready_for_delivery}</span>
							</div>
							<div class="halo-action-pill" data-filter="invoice">
								<i class="fa fa-calculator text-primary"></i>
								<span>${__("Deliveries Ready for Invoicing")}</span>
								<span class="halo-pill-count">${c.pending_invoices}</span>
							</div>
							<div class="halo-action-pill warning" data-filter="payments">
								<i class="fa fa-money text-warning"></i>
								<span>${__("Outstanding Invoices")}</span>
								<span class="halo-pill-count">${c.outstanding_invoices}</span>
							</div>
						</div>
						<div class="card p-3">
							<h6>${__("Action Center Detail View")}</h6>
							<p class="text-muted small">${__("Click any metric above or switch to Pending Fulfillment to trigger immediate document actions.")}</p>
						</div>
					`;
					$slot.html(html);
				}
			},
		});
	}
};
