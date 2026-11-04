# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

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
                    "actionPath": False,
                    "webIcon": None,
                    "webIconData": None,
                    "webIconDataMimetype": None,
                    "backgroundImage": menu.get('backgroundImage'),
                }
            else:
                action = menu['action']
                web_icon = menu['web_icon']
                web_icon_data = menu['web_icon_data']

                if menu['id'] == menu['app_id']:
                    # if it's an app take action of first (sub)child having one defined
                    child = menu
                    while child and not action:
                        action = child['action']
                        child = menus[child['children'][0]] if child['children'] else False

                    webIcon = menu.get('web_icon', '')
                    webIconlist = webIcon and webIcon.split(',')
                    iconClass = color = backgroundColor = None
                    if webIconlist:
                        if len(webIconlist) >= 2:
                            iconClass, color = webIconlist[:2]
                        if len(webIconlist) == 3:
                            backgroundColor = webIconlist[2]

                    if menu.get('web_icon_data'):
                        web_icon_data = re.sub(r'\s/g', "", ('data:%s;base64,%s' % (menu['web_icon_data_mimetype'], menu['web_icon_data'])))
                    elif backgroundColor is not None:  # Could split in three parts?
                        web_icon = ",".join([iconClass or "", color or "", backgroundColor])
                    else:
                        web_icon_data = '/web/static/img/default_icon_app.png'

                action_model, action_id = action.split(',') if action else (False, False)
                action_id = int(action_id) if action_id else False
                if action_model and action_id:
                    action_path = self.env[action_model].browse(action_id).sudo().path
                else:
                    action_path = False

                web_menus[menu['id']] = {
                    "id": menu['id'],
                    "name": menu['name'],
                    "children": menu['children'],
                    "appID": menu['app_id'],
                    "xmlid": menu['xmlid'],
                    "actionID": action_id,
                    "actionModel": action_model,
                    "actionPath": action_path,
                    "webIcon": web_icon,
                    "webIconData": web_icon_data,
                    "webIconDataMimetype": menu['web_icon_data_mimetype'],
                }

        return web_menus
