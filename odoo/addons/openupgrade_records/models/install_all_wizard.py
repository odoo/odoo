# coding: utf-8
# Copyright 2011-2015 Therp BV <https://therp.nl>
# Copyright 2016 Opener B.V. <https://opener.am>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import api, fields, models
from odoo.modules.registry import Registry
from odoo.addons.openupgrade_records.blacklist import BLACKLIST_MODULES


class InstallAll(models.TransientModel):
    _name = 'openupgrade.install.all.wizard'
    _description = 'OpenUpgrade Install All Wizard'
    state = fields.Selection(
        [('init', 'init'), ('ready', 'ready')],
        readonly=True, default='init')
    to_install = fields.Integer(
        'Number of modules to install',
        readonly=True)

    @api.model
    def default_get(self, fields):
        """ Update module list and retrieve the number
        of installable modules """
        res = super(InstallAll, self).default_get(fields)
        update, add = self.env['ir.module.module'].update_list()
        modules = self.env['ir.module.module'].search(
            [('state', 'not in', ['installed', 'uninstallable', 'unknown'])])
        res['to_install'] = len(modules)
        return res

    @api.multi
    def install_all(self):
        """ Main wizard step. Set all installable modules to install
        and actually install them. Exclude testing modules. """
        modules = self.env['ir.module.module'].search([
            ('state', 'not in', ['installed', 'uninstallable', 'unknown']),
            ('category_id.name', '!=', 'Tests'),
            ('name', 'not in', BLACKLIST_MODULES),
        ])
        if modules:
            modules.write({'state': 'to install'})
            self.env.cr.commit()
            Registry.new(self.env.cr.dbname, update_module=True)
            self.write({'state': 'ready'})
        return True
