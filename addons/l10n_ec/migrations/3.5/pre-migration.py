# -*- coding: utf-8 -*-

from odoo import api, SUPERUSER_ID

def update_no_updatable_option_in_l10n_ec_ifrs_record(env):
    # Change the no updatable option to False, in the l10n_ec_ifrs record
    env['ir.model.data'].search([('module', '=', 'l10n_ec'), ('name', '=', 'l10n_ec_ifrs')]).write({'noupdate': False})

def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})
    update_no_updatable_option_in_l10n_ec_ifrs_record(env)