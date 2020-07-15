# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# /odoo/__init__.py is automatically executed first
import odoo.config

entrypoints = {}
def subcommand(func):
    entrypoints[func.__name__.rstrip('_')] = func
    return func


@subcommand
def server():
    pass



entrypoints[odoo.config.subcommand]()
