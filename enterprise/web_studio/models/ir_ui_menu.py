# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval

from odoo import api, models, fields, _
from odoo.http import request

class IrUiMenu(models.Model):
    _name = 'ir.ui.menu'
    _description = 'Menu'
    _inherit = ['studio.mixin', 'ir.ui.menu']

    is_studio_configuration = fields.Boolean(
        string='Studio Configuration Menu',
        help='Indicates that this menu was created by Studio to hold configuration sub-menus',
        readonly=True)

    def write(self, vals):
        """ When renaming a menu will rename the windows action.
        """
        for menu in self:
            if menu._context.get('studio') and 'name' in vals and menu.action:
                menu.action.name = vals['name']
        return super().write(vals)

    @api.model
    def load_menus(self, debug):
        menus = super(IrUiMenu, self).load_menus(debug)
        cids = request and request.cookies.get('cids')
        if cids:
            cids = [int(cid) for cid in cids.split('-')]
        company = self.env['res.company'].browse(cids[0]) \
            if cids and all([cid in self.env.user.company_ids.ids for cid in cids]) \
            else self.env.user.company_id
        menus['root']['backgroundImage'] = bool(company.background_image)
        return menus

    @api.model
    def customize(self, to_move, to_delete):
        """ Apply customizations on menus. The deleted elements will no longer be active.
            When moving a menu, we needed to resequence it. Note that this customization will
                not be kept when upgrading the module (we don't put the ir.model.data in noupdate)

            :param to_move: a dict of modifications with menu ids as keys
                ex: {10: {'parent_id': 1, 'sequence': 0}, 11: {'sequence': 1}}
            :param to_delete: a list of ids
        """

        for menu in to_move:
            menu_id = self.browse(int(menu))
            if 'parent_menu_id' in to_move[menu]:
                menu_id.parent_id = to_move[menu]['parent_menu_id']
            if 'sequence' in to_move[menu]:
                menu_id.sequence = to_move[menu]['sequence']

        self.browse(to_delete).write({'active': False})

        return True

    def _get_studio_configuration_menu(self):
        """
        Get (or create) a configuration menu that will hold some Studio models.

        Creating a model through Studio can create secondary models, such as tags
        or stages. These models need their own menu+action, which should be stored
        under a config menu (child of the app root menu). If this is a Studio app,
        find or create the Configuration menu; if the app is not a Studio app, find or
        create the 'Custom Configuration' menu, to avoid confusion with a potential
        'Configuration' menu which could already be present.
        """
        self.ensure_one()
        root_id = int(self.parent_path.split('/')[0])
        root_xmlids = self.env['ir.model.data'].search_read(
            domain=[('model', '=', 'ir.ui.menu'), ('res_id', '=', root_id)],
            fields=['module', 'name', 'studio']
        )
        # look for a studio config menu in the submenus
        parent_path = '%s/' % root_id
        new_context = dict(self._context)
        new_context.update({'ir.ui.menu.full_list': True})  # allows to create a menu without action
        config_menu = self.with_context(new_context).search([
            ('parent_path', 'like', parent_path), ('is_studio_configuration', '=', True)
        ])
        if not config_menu:
            is_studio_app = root_xmlids and any(map(lambda xmlid: xmlid['studio'], root_xmlids))
            menu_name = _('Configuration') if is_studio_app else _('Custom Configuration')
            config_menu = self.create({
                'name': menu_name,
                'is_studio_configuration': True,
                'parent_id': root_id,
                'sequence': 1000,
            })
        return config_menu
