# -*- coding: utf-8 -*-
{
    "name": "autologin",
    "summary": "Access odoo without password",
    "description": """
Automatically log in as administrator
=====================================

This module automatically authenticates somebody accessing the
login page as admin.

**Security warning** Use this module only on a demo environment
that needs open public access. Don't even think of deploying this
module on an actual production environment.
        """,
    "author": "frePPLe",
    "category": "Uncategorized",
    "version": "12.0.1",
    "depends": ["base", "web"],
    "data": [],
    "demo": [],
    "autoinstall": True,
    "installable": True,
}
