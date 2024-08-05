# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Inventory Operations Traceability in Project Updates',
    'description': """
Access full traceability of inventory operations related to the sales order associated with the
analytic account of your projects in your profitability report.""",
    'summary': """Track inventory operations linked to sales orders in project profitability.""",
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'category': 'Sales',
    'depends': ['sale_project', 'sale_stock', 'project_stock_account'],
    'auto_install': True,
}
