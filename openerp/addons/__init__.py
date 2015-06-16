# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

""" Addons module.

This module serves to contain all OpenERP addons, across all configured addons
paths. For the code to manage those addons, see openerp.modules.

Addons are made available under `openerp.addons` after
openerp.tools.config.parse_config() is called (so that the addons paths are
known).

This module also conveniently reexports some symbols from openerp.modules.
Importing them from here is deprecated.

"""
