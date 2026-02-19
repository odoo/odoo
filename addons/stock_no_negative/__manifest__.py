# ?? 2015-2016 Akretion (http://www.akretion.com)
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).


{
    "name": "Stock Disallow Negative",
    "version": "16.0.1.0.2",
    "category": "Inventory, Logistic, Storage",
    "license": "AGPL-3",
    "summary": "Disallow negative stock levels by default",
    "author": "Akretion,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/stock-logistics-workflow",
    "depends": ["stock"],
    "data": ["views/product_product_views.xml", "views/stock_location_views.xml"],
    "installable": True,
}
