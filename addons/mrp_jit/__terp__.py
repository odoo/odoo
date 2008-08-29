# -*- encoding: utf-8 -*-
{
    "name":"MRP JIT",
    "version":"1.0",
    "author":"Tiny",
    "category":"Generic Modules/Production",
    "description": """
    This module allows Just In Time computation of all procurement.

    If you install this module, you will not have to run the schedulers anymore.
    Each document is computed in realtime. Note that this module can slow down your
    system a little bit.

    It may also increase your stock size because products are reserved as soon
    as possible. In that case, you can not use priorities anymore on the different
    pickings.
    """,
    "depends":["mrp","sale"],
    "demo_xml":[],
    "update_xml":["mrp_jit.xml"],
    "active":False,
    "installable":True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

