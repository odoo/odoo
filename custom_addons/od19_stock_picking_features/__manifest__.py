# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Stock Picking Features",
    "version": "19.0.1.0.0",
    "author": "OD19",
    "category": "Inventory/Operations",
    "summary": "Additional print lines and signature chain auto-resolve on stock.picking",
    "description": """
OD19 Stock Picking Features
===========================

Adds the following capabilities to stock.picking (Delivery Orders /
Receipts / Internal Transfers):

1. Additional print lines
   A new model ``od19.stock.picking.additional.line`` lets warehouse
   users attach free-form lines (description, quantity, unit of measure)
   to a picking. These lines are shown inline on the picking form and
   are intended to be printed together with the standard operations.

2. Signature chain auto-resolve

   Two new fields are added to stock.picking:

   * ``od19_sale_user_id``   - the salesperson from the linked SO.
   * ``od19_dept_manager_id`` - the department manager of that
     salesperson (``hr.department.manager_id.user_id``).

   When the picking is linked to a sale order (either directly through
   ``sale_id`` or by matching ``origin`` to ``sale.order.name``) the
   salesperson and the department manager are resolved automatically.
""",
    "depends": [
        "stock",
        "sale_stock",
        "hr",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/stock_picking_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_stock_picking_features/static/description/icon.svg",
}
