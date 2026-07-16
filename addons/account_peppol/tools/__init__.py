# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from . import demo_utils


def format_list(env, lst):
    """Simplified version of `odoo.tools.format_list` from 18.0 to backport the 18.0 code more easily / safely"""
    return ", ".join(lst)
