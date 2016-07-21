import frappe
import requests.exceptions
from erpnext_shopify.shopify_requests import post_request
from frappe.utils import cint
from erpnext_shopify.utils import disable_shopify_sync_for_item, make_shopify_log
from erpnext_shopify.sync_products import get_erpnext_items_to_sync, get_variant_attributes
from frappe.utils.background_jobs import enqueue

def execute():
	"""enqueuing patch execution for long job, as patch will pull all missing data it 
		may take time more than 4-5 mins"""

	enqueue("erpnext_shopify.patches.V2_0.sync_missing_variants.sync_missing_variants", queue='long')

def sync_missing_variants():
	shopify_settings = frappe.get_doc("Shopify Settings")
	
	for item in get_erpnext_items_to_sync():
		products = {}
		variant_item_code_list = []
				
		if not cint(item.has_variants):
			continue

		variant_list, options, variant_item_name = get_variant_attributes(item, shopify_settings.price_list,
			shopify_settings.warehouse, include_varaint_id=False)

		variant_item_code_list.extend(variant_item_name)

		erp_item = frappe.get_doc("Item", item.name)
		
		for idx, variant in enumerate(variant_list):
			products["variant"] = variant
			try:
				new_variant = post_request("/admin/products/{0}/variants.json".format(item.get("shopify_product_id")),
					products)

				update_variant(new_variant, variant_item_code_list[idx])
				frappe.db.commit()

			except requests.exceptions.HTTPError, e:
				if e.args[0] and e.args[0].startswith("404"):
					disable_shopify_sync_for_item(erp_item, rollback=True)

				make_shopify_log(title=e.message, status="Error", method="sync_shopify_items",
					message=frappe.get_traceback(), request_data=item, exception=True)

def update_variant(new_variant, existing_variant_item_code):
	item_details = frappe.db.get_value("Item", existing_variant_item_code,
		["shopify_variant_id", "name"], as_dict=1)
	
	if item_details.name == item_details.shopify_variant_id:
		frappe.rename_doc("Item", item_details.name, new_variant["variant"]["id"])
		
	frappe.db.set_value("Item", existing_variant_item_code, "shopify_variant_id", new_variant["variant"]["id"])
	