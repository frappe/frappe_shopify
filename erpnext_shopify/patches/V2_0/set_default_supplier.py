# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
# License: GNU General Public License v3. See license.txt
import frappe
from erpnext_shopify.shopify_requests import get_shopify_items
from erpnext_shopify.sync_products import get_supplier

def execute():
	for shopify_item in get_shopify_items(ignore_filter_conditions=True):
		name = frappe.db.get_value("Item", {"shopify_product_id": shopify_item.get("id")}, "name")
		if name:
			frappe.db.set_value("Item", name, "default_supplier", get_supplier(shopify_item), update_modified=False)
	frappe.db.commit()		
			
			