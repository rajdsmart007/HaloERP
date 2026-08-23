/* HaloWorkflowHeader — Reusable Interactive Stage Component */

frappe.provide("haloerp.workflow");

haloerp.workflow.HaloWorkflowHeader = class HaloWorkflowHeader {
	constructor(opts) {
		this.wrapper = opts.wrapper;
		this.doctype = opts.doctype;
		this.docname = opts.docname;
		this.frm = opts.frm;
		this.data = null;
		this.init();
	}

	init() {
		this.render_loading();
		this.fetch_data();
	}

	render_loading() {
		this.$container = $('<div class="halo-workflow-header-container"></div>').appendTo(this.wrapper.empty());
		this.$container.html(`
			<div class="text-muted text-center" style="font-size: 12px; padding: 6px;">
				<i class="fa fa-spinner fa-spin"></i> ${__("Loading HaloERP Sales & Procurement Workflow...")}
			</div>
		`);
	}

	fetch_data() {
		frappe.call({
			method: "haloerp.controllers.sales_procurement_controller.get_workflow_summary",
			args: {
				doctype: this.doctype,
				name: this.docname,
			},
			callback: (r) => {
				if (r.message) {
					this.data = r.message;
					this.render();
				}
			},
		});
	}

	render() {
		if (!this.data) return;

		const stages = [
			{ key: "enquiry", label: __("Enquiry"), icon: "fa-bullhorn" },
			{ key: "quotation", label: __("Quotation"), icon: "fa-file-text-o" },
			{ key: "customer_po", label: __("Customer PO"), icon: "fa-check-square-o" },
			{ key: "sales_order", label: __("Sales Orders"), icon: "fa-shopping-cart" },
			{ key: "procurement", label: __("Procurement"), icon: "fa-truck" },
			{ key: "receipt", label: __("Goods Receipt"), icon: "fa-archive" },
			{ key: "delivery", label: __("Delivery"), icon: "fa-paper-plane-o" },
			{ key: "invoice", label: __("Invoice"), icon: "fa-calculator" },
			{ key: "payment", label: __("Payment"), icon: "fa-money" },
		];

		const status_badge_class = this.get_status_badge_class(this.data.status);

		let html = `
			<div class="halo-workflow-title-row">
				<div class="halo-workflow-title">
					<i class="fa fa-sitemap" style="color: #1769e0;"></i>
					<span>${__("Sales & Procurement Workflow")}</span>
					${this.data.customer_name ? `<span class="text-muted" style="font-weight: 500;">— ${this.data.customer_name}</span>` : ""}
				</div>
				<div>
					<span class="halo-workflow-status-badge ${status_badge_class}">
						${this.data.status || __("Active")}
					</span>
					<button class="btn btn-xs btn-default ml-2 btn-open-control-center" title="${__("Open in Control Center")}">
						<i class="fa fa-external-link"></i> ${__("Control Center")}
					</button>
				</div>
			</div>
			<div class="halo-workflow-stages">
		`;

		stages.forEach((stage, idx) => {
			const s_data = this.data.stages[stage.key] || { status: "gray", count: 0, docs: [] };
			const icon_content = s_data.status === "green" ? "✓" : (s_data.count > 0 ? s_data.count : idx + 1);

			html += `
				<div class="halo-workflow-stage-item" data-stage="${stage.key}">
					<div class="halo-stage-icon-circle ${s_data.status}">
						${icon_content}
					</div>
					<div class="halo-stage-label">${stage.label}</div>
					<div class="halo-stage-count">${s_data.count > 0 ? `${s_data.count} doc(s)` : "-"}</div>
				</div>
			`;

			if (idx < stages.length - 1) {
				html += `<div class="halo-stage-arrow">→</div>`;
			}
		});

		html += `</div>`;
		this.$container.html(html);

		// Event handlers
		this.$container.find(".halo-workflow-stage-item").on("click", (e) => {
			const stageKey = $(e.currentTarget).data("stage");
			this.show_stage_details(stageKey);
		});

		this.$container.find(".btn-open-control-center").on("click", () => {
			frappe.set_route("sales-procurement-center", {
				doctype: this.doctype,
				name: this.docname,
			});
		});
	}

	get_status_badge_class(status) {
		if (["Completed", "Submitted", "Paid", "Delivered"].includes(status)) return "green";
		if (["Draft", "Pending", "Partially Delivered", "Partially Invoiced"].includes(status)) return "orange";
		if (["Cancelled", "Stopped"].includes(status)) return "red";
		return "blue";
	}

	show_stage_details(stageKey) {
		const s_data = this.data.stages[stageKey];
		if (!s_data || !s_data.docs.length) {
			frappe.msgprint(__("No linked documents found for stage: {0}", [s_data.label || stageKey]));
			return;
		}

		let list_html = `<div class="list-group">`;
		s_data.docs.forEach((doc) => {
			const dt = doc.doctype || this.get_doctype_for_stage(stageKey);
			list_html += `
				<a href="/app/${frappe.router.slug(dt)}/${doc.name}" class="list-group-item list-group-item-action flex-column align-items-start">
					<div class="d-flex w-100 justify-content-between">
						<h6 class="mb-1" style="font-weight: 600; color: #1769e0;">${doc.name}</h6>
						<small class="badge badge-info">${doc.status || __("Active")}</small>
					</div>
					<small class="text-muted">${doc.posting_date || doc.transaction_date || ""} ${doc.grand_total ? `— ${format_currency(doc.grand_total, this.data.currency)}` : ""}</small>
				</a>
			`;
		});
		list_html += `</div>`;

		frappe.msgprint({
			title: s_data.label,
			message: list_html,
			indicator: s_data.status === "green" ? "green" : "blue",
		});
	}

	get_doctype_for_stage(stageKey) {
		const map = {
			enquiry: "Opportunity",
			quotation: "Quotation",
			customer_po: "Sales Order",
			sales_order: "Sales Order",
			procurement: "Purchase Order",
			receipt: "Purchase Receipt",
			delivery: "Delivery Note",
			invoice: "Sales Invoice",
			payment: "Payment Entry",
		};
		return map[stageKey] || "Sales Order";
	}
};
