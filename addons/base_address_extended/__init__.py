# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from . import models

from odoo import api, SUPERUSER_ID


def _split_street_after_install(cr, registry):
    """Re-run _split_street after processing the data files to handle
    contacts with a specific format"""
    env = api.Environment(cr, SUPERUSER_ID, {})

    countries = env['res.country'].search([
        ('street_format', '!=', models.base_address_extended.DEFAULT_STREET_FORMAT),
    ])
    partners = env['res.partner'].search([
        ('country_id', 'in', countries.ids),
        ('street', '!=', ''),
    ])
    partners._split_street()
