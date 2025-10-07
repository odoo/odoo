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

    local_updatable = fields.Boolean('Local updatable', compute=False, default=False, store=True)
    addons_path_id = fields.Many2one('ir.module.addons.path', string='Addons Path ID', readonly=True)
    addons_path = fields.Char(string='Addons Path', related='addons_path_id.path', readonly=True)
    license = fields.Char(readonly=True)

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
        modules = self.filtered(lambda r: r.state == 'installed')
        # 先清理, odoo原生经常清理不干净
        # odoo 16中，不再使用 ir.translation，直接使用json字段
        # for rec in modules:
        #     translate = self.env['ir.translation'].search([
        #         ('lang', '=', lang),
        #         ('module', '=', rec.name)
        #     ])
        #     translate.sudo().unlink()
        # 再重载
        modules._update_translations(filter_lang=lang, overwrite=True)
        # odoo 16翻译模式改变，仍需更新模块
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'target': 'new',
            'params': {
                'message': _("The languages that you selected have been successfully update.\
                            You still need to Upgrade the apps to make it worked."),
                'type': 'success',
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def button_get_po(self):
        self.ensure_one()
        action = self.env.ref('app_odoo_customize.action_server_module_multi_get_po').sudo().read()[0]
        action['context'].update({
                'default_lang': self.env.user.lang,
            })
        return action

    def update_list(self):
        res = super(IrModule, self).update_list()
        default_version = modules.adapt_version('1.0')
        known_mods = self.with_context(lang=None).search([])
        known_mods_names = {mod.name: mod for mod in known_mods}
        # 处理可更新字段， 不要compute，会出错
        for mod_name in modules.get_modules():
            mod = known_mods_names.get(mod_name)
            if mod:
                installed_version = self.get_module_info(mod.name).get('version', default_version)
                if installed_version and mod.latest_version and operator.gt(installed_version, mod.latest_version):
                    local_updatable = True
                else:
                    local_updatable = False
                if mod.local_updatable != local_updatable:
                    mod.write({'local_updatable': local_updatable})
            
        return res
