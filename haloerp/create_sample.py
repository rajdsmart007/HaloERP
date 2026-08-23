import frappe
from frappe.utils import nowdate, add_days, flt

def run():
    company = "Halo Enterprises" if frappe.db.exists("Company", "Halo Enterprises") else frappe.get_all("Company", limit=1)[0].name

    # 1. Customer
    customer_name = "ABC Corporation"
    if not frappe.db.exists("Customer", customer_name):
        c = frappe.new_doc("Customer")
        c.customer_name = customer_name
        c.customer_type = "Company"
        c.customer_group = "Commercial"
        c.territory = "Saudi Arabia"
        c.insert(ignore_permissions=True)

    # 2. Suppliers
    for s_name in ["Supplier A", "Supplier B", "Supplier C"]:
        if not frappe.db.exists("Supplier", s_name):
            s = frappe.new_doc("Supplier")
            s.supplier_name = s_name
            s.supplier_type = "Company"
            s.supplier_group = "Local"
            s.insert(ignore_permissions=True)

    # 3. Items
    items_data = [
        {"item_code": "ITEM-001", "item_name": "Product A", "is_stock_item": 1, "standard_rate": 100, "item_group": "Products"},
        {"item_code": "ITEM-002", "item_name": "Product B", "is_stock_item": 1, "standard_rate": 150, "item_group": "Products"},
        {"item_code": "ITEM-003", "item_name": "Procured Material C", "is_stock_item": 0, "standard_rate": 200, "item_group": "Raw Material"},
    ]
    for itm in items_data:
        if not frappe.db.exists("Item", itm["item_code"]):
            i = frappe.new_doc("Item")
            i.item_code = itm["item_code"]
            i.item_name = itm["item_name"]
            i.item_group = itm["item_group"]
            i.stock_uom = "Nos"
            i.is_stock_item = itm["is_stock_item"]
            i.standard_rate = itm["standard_rate"]
            i.insert(ignore_permissions=True)

    # 4. Quotation (QT-00001)
    q = frappe.new_doc("Quotation")
    q.quotation_to = "Customer"
    q.party_name = customer_name
    q.company = company
    q.transaction_date = nowdate()
    q.order_type = "Sales"

    q.append("items", {"item_code": "ITEM-001", "qty": 5, "rate": 100})
    q.append("items", {"item_code": "ITEM-002", "qty": 3, "rate": 150})
    q.append("items", {"item_code": "ITEM-003", "qty": 2, "rate": 200})

    q.insert(ignore_permissions=True)
    q.submit()
    print(f"Created & Submitted Quotation: {q.name}")

    # 5. Create First Partial Sales Order (SO-1) via our controller
    from haloerp.controllers.sales_procurement_controller import create_partial_sales_order, create_multi_supplier_purchase_orders

    so1_name = create_partial_sales_order(
        quotation=q.name,
        items_allocation=[
            {"quotation_item": q.items[0].name, "allocate_qty": 3},
        ],
        customer_po_no="ABC-PO-1001"
    )
    so1 = frappe.get_doc("Sales Order", so1_name)
    so1.delivery_date = add_days(nowdate(), 7)
    so1.save(ignore_permissions=True)
    so1.submit()
    print(f"Created & Submitted Sales Order 1: {so1.name}")

    # 6. Create Multi-Supplier Purchase Orders against SO-1
    po_list = create_multi_supplier_purchase_orders(
        sales_order=so1.name,
        supplier_allocation=[
            {
                "supplier": "Supplier A",
                "items": [{"item_code": "ITEM-001", "sales_order_item": so1.items[0].name, "qty": 3, "rate": 80}]
            }
        ]
    )
    for p_name in po_list:
        p = frappe.get_doc("Purchase Order", p_name)
        p.submit()
        print(f"Created & Submitted PO: {p.name} for Supplier A")

    # 7. Create Second Sales Order (SO-2) for remaining items
    so2_name = create_partial_sales_order(
        quotation=q.name,
        items_allocation=[
            {"quotation_item": q.items[0].name, "allocate_qty": 2},
            {"quotation_item": q.items[1].name, "allocate_qty": 3},
            {"quotation_item": q.items[2].name, "allocate_qty": 2},
        ],
        customer_po_no="ABC-PO-1002"
    )
    so2 = frappe.get_doc("Sales Order", so2_name)
    so2.delivery_date = add_days(nowdate(), 10)
    so2.save(ignore_permissions=True)
    print(f"Created Draft Sales Order 2: {so2.name}")

    frappe.db.commit()
    print("Sample workflow data setup completed successfully!")

if __name__ == "__main__":
    run()
