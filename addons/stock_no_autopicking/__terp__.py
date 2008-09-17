# -*- encoding: utf-8 -*-
{
    "name":"Stock No Auto-Picking",
    "version":"1.0",
    "author":"Tiny",
    "category":"Generic Modules/Production",
    "description": """
    This module allows an intermediate picking process to provide raw materials
    to production orders.

    One example of usage of this module is to manage production made by your
    suppliers (sub-contracting). To achieve this, set the assembled product
    which is sub-contracted to "No Auto-Picking" and put the location of the
    supplier in the routing of the assembly operation.
    """,
    "depends":["mrp"],
    "demo_xml":[],
    "update_xml":["stock_no_autopicking_view.xml"],
    "active":False,
    "installable":True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

