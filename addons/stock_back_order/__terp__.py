# -*- encoding: utf-8 -*-
{
    "name" : "Stock Back Order",
    "version" : "1.0",
    "author" : "Tiny",
    "depends" : ["base", "stock",],
    "category" : "Generic Modules/Inventory Control",
    "description":"""
    To manage all back-orders (means partial pickings):
    When products coming from suppliers arrive but some are missing, we have to make a partial picking.
    The remaining products are called "back-orders" and have to be separated from normal waiting picking (in a predefined list called "Back-Orders").
    The same process has to be done for sending goods.

    """,
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : ["stock_view.xml","stock_wizard.xml"],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

