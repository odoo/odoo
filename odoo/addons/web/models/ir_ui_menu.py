# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def load_web_menus(self, debug):
        """ Loads all menu items (all applications and their sub-menus) and
        processes them to be used by the webclient. Mainly, it associates with
        each application (top level menu) the action of its first child menu
        that is associated with an action (recursively), i.e. with the action
        to execute when the opening the app.

        :return: the menus (including the images in Base64)
        """
        menus = self.load_menus(debug)

        web_menus = {}
        for menu in menus.values():
            if not menu['id']:
                # special root menu case
                web_menus['root'] = {
                    "id": 'root',
                    "name": menu['name'],
                    "children": menu['children'],
                    "appID": False,
                    "xmlid": "",
                    "actionID": False,
                    "actionModel": False,
                    "webIcon": None,
                    "webIconData": None,
                    "webIconDataMimetype": None,
                    "backgroundImage": menu.get('backgroundImage'),
                }
            else:
                action = menu['action']

                if menu['id'] == menu['app_id']:
                    # if it's an app take action of first (sub)child having one defined
                    child = menu
                    while child and not action:
                        action = child['action']
                        child = menus[child['children'][0]] if child['children'] else False

                action_model, action_id = action.split(',') if action else (False, False)
                action_id = int(action_id) if action_id else False

                web_menus[menu['id']] = {
                    "id": menu['id'],
                    "name": menu['name'],
                    "children": menu['children'],
                    "appID": menu['app_id'],
                    "xmlid": menu['xmlid'],
                    "actionID": action_id,
                    "actionModel": action_model,
                    "webIcon": menu['web_icon'],
                    "webIconData": menu['web_icon_data'],
                    "webIconDataMimetype": menu['web_icon_data_mimetype'],
                }

        return web_menus
