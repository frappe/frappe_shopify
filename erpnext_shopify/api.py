# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe import _
from .exceptions import ShopifyError
from .sync_orders import sync_orders
from .sync_customers import sync_customers
from frappe.utils.user import get_system_managers
from .sync_products import sync_products, update_item_stock_qty
from .utils import disable_shopify_sync_on_exception, create_log_entry

@frappe.whitelist()
def sync_shopify():
	"Enqueue longjob for syncing shopify"
	from frappe.tasks import scheduler_task
	scheduler_task.delay(site=frappe.local.site, event="hourly_long", 
		handler="erpnext_shopify.api.sync_shopify_resources")
	frappe.msgprint(_("Queued for syncing. It may take a few minutes to an hour if this is your first sync."))

@frappe.whitelist()
def sync_shopify_resources():
	shopify_settings = frappe.get_doc("Shopify Settings")
	if shopify_settings.enable_shopify:
		try :
			validate_shopify_settings(shopify_settings)
			sync_products(shopify_settings.price_list, shopify_settings.warehouse)
			sync_customers()
			sync_orders()
			update_item_stock_qty()
			
			frappe.db.set_value("Shopify Settings", None, "last_sync_datetime", frappe.utils.now())
			
			subject = _("Shopify Sync has completed")
			content = _(""" Shopify ERPnext sync is completed at %s. """%shopify_settings.last_sync_datetime)
			
			send_notification_email(subject, content)
			
		except Exception, e:
			disable_shopify_sync_on_exception()
			
			subject = _("Shopify Sync has been disabled")
			
			if e.args[0] and e.args[0].startswith("402"):
				content = _("""Shopify has suspended your account till you complete the payment. We have disabled ERPNext Shopify Sync. Please enable it once your complete the payment at Shopify.""")
				
			else:
				content = _("""Unfortunately shopify sync has terminated. Please check Scheduler Log for more details.""")
				create_log_entry(e.message, {}, frappe.get_traceback())
				
			send_notification_email(subject=subject, content=content)
			
	elif frappe.local.form_dict.cmd == "erpnext_shopify.api.sync_shopify":
		frappe.throw(_("""Shopify connector is not enabled. Click on 'Connect to Shopify' to connect ERPNext and your Shopify store."""))

def validate_shopify_settings(shopify_settings):
	"""
		This will validate mandatory fields and access token or app credentials 
		by calling validate() of shopify settings.
	"""
	try:
		shopify_settings.save()
	except ShopifyError:
		disable_shopify_sync_on_exception()

def send_notification_email(subject, content):
	frappe.sendmail(get_system_managers(), subject=subject, content=content)