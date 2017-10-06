# coding: utf-8
# Copyright 2011-2015 Therp BV <https://therp.nl>
# Copyright 2016 Opener B.V. <https://opener.am>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.exceptions import UserError
from openupgradelib import openupgrade_tools
from odoo.modules.registry import Registry


class GenerateWizard(models.TransientModel):
    _name = 'openupgrade.generate.records.wizard'
    _description = 'OpenUpgrade Generate Records Wizard'
    _rec_name = 'state'
    state = fields.Selection(
        [('init', 'init'), ('ready', 'ready')], default='init')

    @api.multi
    def generate(self):
        """ Main wizard step. Make sure that all modules are up-to-date,
        then reinitialize all installed modules.
        Equivalent of running the server with '-d <database> --init all'

        The goal of this is to fill the records table.

        TODO: update module list and versions, then update all modules? """
        # Truncate the records table
        if (openupgrade_tools.table_exists(
            self.env.cr, 'openupgrade_attribute') and
                openupgrade_tools.table_exists(
                    self.env.cr, 'openupgrade_record')):
            self.env.cr.execute(
                'TRUNCATE openupgrade_attribute, openupgrade_record;'
                )

        # Need to get all modules in state 'installed'
        modules = self.env['ir.module.module'].search(
            [('state', 'in', ['to install', 'to upgrade'])])
        if modules:
            self.env.cr.commit()
            Registry.new(self.env.cr.dbname, update_module=True)
        # Did we succeed above?
        modules = self.env['ir.module.module'].search(
            [('state', 'in', ['to install', 'to upgrade'])])
        if modules:
            raise UserError(
                "Cannot seem to install or upgrade modules %s" % (
                    ', '.join([module.name for module in modules])))
        # Now reinitialize all installed modules
        self.env['ir.module.module'].search(
            [('state', '=', 'installed')]).write(
                {'state': 'to install'})
        self.env.cr.commit()
        Registry.new(self.env.cr.dbname, update_module=True)
        return self.write({'state': 'ready'})
