# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, tools


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    load_xmlid = fields.Boolean(default=False)

    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang',))
    def load_menus(self, debug):
        """ Extends load_menus to include requested xmlids """
        menu_root = super(IrUiMenu, self).load_menus(debug)

        menu_ids = [menu.id for menu in self.browse(menu_root['all_menu_ids']) if menu.load_xmlid]
        xmlids = {
            d.res_id: d.module + "." + d.name
            for d in self.env['ir.model.data'].search([('res_id', 'in', menu_ids), ('model', '=', 'ir.ui.menu')])
        }

        def _find_subtree(tree, node_id):
            # Returns the subtree whose id is node_id
            if tree['id'] == node_id:
                return tree
            else:
                for child in tree['children']:
                    subtree = _find_subtree(child, node_id)
                    if subtree:
                        return subtree

        for menu_id, menu_xmlid in xmlids.iteritems():
            _find_subtree(menu_root, menu_id)['xmlid'] = menu_xmlid

        return menu_root
