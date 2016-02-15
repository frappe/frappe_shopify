# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.utils import get_url
from .exceptions import ShopifyWebhookSetupError
from .shopify_requests import get_request, post_request, get_shopify_settings, delete_request

def create_webhooks():
	settings = get_shopify_settings()
	if not settings.is_webhook_created and settings.enable_shopify:
		for event in ["customers/enable","customers/disable", "customers/delete", "products/delete"]:
			create_webhook(event)
		frappe.db.set_value("Shopify Settings", None, "is_webhook_created", 1)
		frappe.db.commit()

def create_webhook(topic):
	try:
		# replace address with get_url
		post_request('admin/webhooks.json', {
			"webhook": {
				"topic": topic,
				"address": "https://erpnext.localtunnel.me/api/method/erpnext_shopify.shopify_webhooks_handler.webhook_handler",
				"format": "json"
			}
		})
	except ShopifyWebhookSetupError, e:
		raise e

def get_webhooks():
	webhooks = get_request("/admin/webhooks.json")
	return webhooks["webhooks"]

def delete_webhooks():
	webhooks = get_webhooks()
	for webhook in webhooks:
		delete_request("/admin/webhooks/{}.json".format(webhook['id']))
