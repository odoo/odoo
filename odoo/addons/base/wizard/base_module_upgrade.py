# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class BaseModuleUpgrade(models.TransientModel):
    _name = "base.module.upgrade"
    _description = "Upgrade Module"

    @api.model
    @api.returns('ir.module.module')
    def get_module_list(self):
        states = ['to upgrade', 'to remove', 'to install']
        return self.env['ir.module.module'].search([('state', 'in', states)])

    @api.model
    def _default_module_info(self):
        return "\n".join("%s: %s" % (mod.name, mod.state) for mod in self.get_module_list())

    module_info = fields.Text('Apps to Update', readonly=True, default=_default_module_info)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(BaseModuleUpgrade, self).fields_view_get(view_id, view_type, toolbar=toolbar,submenu=False)
        if view_type != 'form':
            return res

        if not(self._context.get('active_model') and self._context.get('active_id')):
            return res

        if not self.get_module_list():
            res['arch'] = '''<form string="Upgrade Completed">
                                <separator string="Upgrade Completed" colspan="4"/>
                                <footer>
                                    <button name="config" string="Start Configuration" type="object" class="btn-primary" data-hotkey="q"/>
                                    <button special="cancel" data-hotkey="z" string="Close" class="btn-secondary"/>
                                </footer>
                             </form>'''

        return res

    def upgrade_module_cancel(self):
        Module = self.env['ir.module.module']
        to_install = Module.search([('state', 'in', ['to upgrade', 'to remove'])])
        to_install.write({'state': 'installed'})
        to_uninstall = Module.search([('state', '=', 'to install')])
        to_uninstall.write({'state': 'uninstalled'})
        return {'type': 'ir.actions.act_window_close'}

    def upgrade_module(self):
        Module = self.env['ir.module.module']

        # install/upgrade: double-check preconditions
        mods = Module.search([('state', 'in', ['to upgrade', 'to install'])])
        if mods:
            query = """ SELECT d.name
                        FROM ir_module_module m
                        JOIN ir_module_module_dependency d ON (m.id = d.module_id)
                        LEFT JOIN ir_module_module m2 ON (d.name = m2.name)
                        WHERE m.id in %s and (m2.state IS NULL or m2.state IN %s) """
            self._cr.execute(query, (tuple(mods.ids), ('uninstalled',)))
            unmet_packages = [row[0] for row in self._cr.fetchall()]
            if unmet_packages:
                raise UserError(_('The following modules are not installed or unknown: %s') % ('\n\n' + '\n'.join(unmet_packages)))

            mods.download()

        # terminate transaction before re-creating cursor below
        self._cr.commit()
        odoo.modules.registry.Registry.new(self._cr.dbname, update_module=True)
        self._cr.reset()

        return {'type': 'ir.actions.act_window_close'}

    def config(self):
        # pylint: disable=next-method-called
        return self.env['res.config'].next()
