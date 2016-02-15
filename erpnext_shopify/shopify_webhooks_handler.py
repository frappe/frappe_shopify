# -*- coding: utf-8 -*-
# Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
import hashlib, base64, hmac, json
from functools import wraps
from .shopify_requests import get_shopify_settings
from frappe.exceptions import AuthenticationError

handler_map = {
	"customers/enable": "erpnext_shopify.sync_customers.enable_customer",
	"customers/disable": "erpnext_shopify.sync_customers.disable_customer", 
	"customers/delete": "erpnext_shopify.sync_customers.disable_customer", 
	"products/delete": "erpnext_shopify.sync_products.disable_item"
}


def shopify_webhook(f):
	"""
	A decorator thats checks and validates a Shopify Webhook request.
	"""

	def _hmac_is_valid(body, secret, hmac_to_verify):
		secret = str(secret)
		hash = hmac.new(secret, body, hashlib.sha256)
		hmac_calculated = base64.b64encode(hash.digest())
		return hmac_calculated == hmac_to_verify

	@wraps(f)
	def wrapper(*args, **kwargs):
		# Try to get required headers and decode the body of the request.
		webhook_topic = frappe.local.request.headers.get('X-Shopify-Topic')
		webhook_hmac	= frappe.local.request.headers.get('X-Shopify-Hmac-Sha256')
		webhook_data	= frappe._dict(json.loads(frappe.local.request.get_data()))

		# Verify the HMAC.
		shopify_settings = get_shopify_settings()
		if shopify_settings.password:
			if not _hmac_is_valid(frappe.local.request.get_data(), shopify_settings.shared_secret, webhook_hmac):
				raise AuthenticationError()

			# Otherwise, set properties on the request object and return.
		frappe.local.request.webhook_topic = webhook_topic
		frappe.local.request.webhook_data  = webhook_data
		kwargs.pop('cmd')

		return f(*args, **kwargs)
	return wrapper


@frappe.whitelist(allow_guest=True)
@shopify_webhook
def webhook_handler():
	topic = frappe.local.request.webhook_topic
	data = frappe.local.request.webhook_data
	
	if not frappe.db.get_value("Webhook Request Handler", {"request_data": json.dumps(data)}, "name"):
		webhook_handler = frappe.new_doc("Webhook Request Handler")
		webhook_handler.event = topic
		webhook_handler.request_data = json.dumps(data)
		webhook_handler.handler = handler_map.get(topic)
		webhook_handler.save(ignore_permissions=True)

def call_shopify_webhooks_event_handler():
	for webhook_request in frappe.get_all("Webhook Request Handler", 
		filters={"status": "In Queue"}, fields=["*"]):
		frappe.get_attr(webhook_request.handler)(webhook_request)
