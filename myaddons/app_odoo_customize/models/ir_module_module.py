# -*- coding: utf-8 -*-

from odoo import api, fields, models, modules, tools, _

import operator

class IrModule(models.Model):
    _inherit = 'ir.module.module'

    # attention: Incorrect field names !!
    #   installed_version refers the latest version (the one on disk)
    #   latest_version refers the installed version (the one in database)
    #   published_version refers the version available on the repository
    # installed_version = fields.Char('Latest Version', compute='_get_latest_version')
    # latest_version = fields.Char('Installed Version', readonly=True)

    local_updatable = fields.Boolean('Local updatable', compute='_get_latest_version', compute_sudo=False, default=False, store=True)

    def module_multi_uninstall(self):
        """ Perform the various steps required to uninstall a module completely
            including the deletion of all database structures created by the module:
            tables, columns, constraints, etc.
        """
        modules = self.browse(self.env.context.get('active_ids'))
        [module.button_immediate_uninstall() for module in modules if module not in ['base', 'web']]

    # 更新翻译，当前语言
    def module_multi_refresh_po(self):
        lang = self.env.user.lang
        modules = self.browse(self.env.context.get('active_ids'))
        # 先清理, odoo原生经常清理不干净
        for rec in modules:
            translate = self.env['ir.translation'].search([
                ('lang', '=', lang),
                ('module', '=', rec.name)
            ])
            translate.sudo().unlink()
        # 再重载
        self.sudo().with_context(overwrite=True)._update_translations(lang)

    def button_get_po(self):
        self.ensure_one()
        action = self.env.ref('app_odoo_customize.action_server_module_multi_get_po').read()[0]
        action['context'].update({
                'default_lang': self.env.user.lang,
            })
        return action

    @api.depends('name', 'latest_version', 'state')
    def _get_latest_version(self):
        default_version = modules.adapt_version('1.0')
        for module in self:
            module.installed_version = self.get_module_info(module.name).get('version', default_version)
            if module.installed_version and module.latest_version and operator.gt(module.installed_version, module.latest_version):
                module.local_updatable = True
            else:
                module.local_updatable = False

