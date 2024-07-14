# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo import models


class IrUiMenu(models.Model):
    _inherit = "ir.ui.menu"

    def load_web_menus(self, debug):
        menus = super(IrUiMenu, self).load_web_menus(debug)

        for menu in menus.values():
            # web icons for app root menus
            if menu['id'] == menu['appID']:
                webIcon = menu.get('webIcon', '')
                webIconlist = webIcon and webIcon.split(',')
                iconClass = color = backgroundColor = None
                if webIconlist:
                    if len(webIconlist) >= 2:
                        iconClass, color = webIconlist[:2]
                    if len(webIconlist) == 3:
                        backgroundColor = webIconlist[2]

                if menu.get('webIconData'):
                    menu['webIconData'] = re.sub(r'\s/g', "", ('data:%s;base64,%s' % (menu['webIconDataMimetype'], menu['webIconData'].decode('utf-8'))))
                elif backgroundColor is not None:  # Could split in three parts?
                    menu['webIcon'] = ",".join([iconClass or "", color or "", backgroundColor])
                else:
                    menu['webIconData'] = '/web_enterprise/static/img/default_icon_app.png'

        return menus
