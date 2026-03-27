# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, modules


class Users(models.Model):
    _name = 'res.users'
    _inherit = ['res.users']

    @api.model
    def _get_activity_groups(self):
        """ Update the systray icon of res.partner activities to use the
        contact application one instead of base icon. """
        activities = super()._get_activity_groups()
        for activity in activities:
            if activity['model'] != 'res.partner':
                continue
            activity['icon'] = modules.module.get_module_icon('contacts')
        return activities

    @api.model
    def _contacts_apply_menu_labels(self):
        env = self.sudo().with_context(lang='en_US').env
        lang_model = env['res.lang']

        def _write_translated_name(record, value):
            if not record:
                return
            record.with_context(lang='en_US').write({'name': value})
            for code in ('es_ES', 'es_419'):
                if lang_model.search_count([('code', '=', code)]):
                    record.with_context(lang=code).write({'name': value})

        root_menu = env.ref('contacts.menu_contacts', raise_if_not_found=False)
        accounts_menu = env.ref('contacts.res_partner_menu_contacts', raise_if_not_found=False)
        config_menu = env.ref('contacts.res_partner_menu_config', raise_if_not_found=False)
        contacts_action = env.ref('contacts.action_contacts', raise_if_not_found=False)
        crm_contacts_menu = env.ref('crm.menu_crm_all_contacts', raise_if_not_found=False)

        _write_translated_name(root_menu, 'Clientes')
        _write_translated_name(contacts_action, 'Cuentas')
        if accounts_menu:
            _write_translated_name(accounts_menu, 'Cuentas')
            accounts_menu.write({'sequence': 1, 'active': True})
            if root_menu:
                accounts_menu.write({'parent_id': root_menu.id})

        if config_menu:
            config_menu.write({'active': False})

        if crm_contacts_menu:
            _write_translated_name(crm_contacts_menu, 'Contactos')
            crm_contacts_menu.write({'sequence': 2, 'active': True})
            if root_menu:
                crm_contacts_menu.write({'parent_id': root_menu.id})
            duplicate_contacts_menu = env.ref('contacts.res_partner_menu_persons', raise_if_not_found=False)
            if duplicate_contacts_menu:
                duplicate_contacts_menu.write({'active': False})

        if root_menu:
            sibling_menus = env['ir.ui.menu'].search([
                ('parent_id', '=', root_menu.id),
                ('active', '=', True),
            ])
            for menu in sibling_menus:
                if accounts_menu and menu.id == accounts_menu.id:
                    continue
                if crm_contacts_menu and menu.id == crm_contacts_menu.id:
                    continue
                if config_menu and menu.id == config_menu.id:
                    continue
                menu.write({'active': False})
