# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Amazon Connector Channel Management",
    "summary": "Manually select offer's fulfillment channel.",
    "category": "Sales/Sales",
    "sequence": 321,
    "depends": ["sale_amazon"],
    "auto_install": True,
    "data": ["views/amazon_offer_views.xml"],
    "license": "OEEL-1",
}
