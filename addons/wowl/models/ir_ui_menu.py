from odoo import api, fields, models, tools, _


class IrUiMenu(models.Model):

    _inherit = "ir.ui.menu"

    @api.model
    @tools.ormcache_context('self._uid', 'debug', keys=('lang',))
    def load_menus_flat(self, debug):
        menu_data = self.load_menus(debug)
        for app in menu_data['children']:
            child = app
            while not app['action'] and child['children']:
                child = child['children'][0]
                app['action'] = child['action']
        return self._process_flatten(menu_data, None, None)[0]

    @api.model
    def _process_flatten(self, menu_data, appID, accumulator):
        if accumulator is None:
            accumulator = {}
        appID = appID or menu_data['id']
        children = []
        for submenu in menu_data['children']:
            children.append(self._process_flatten(submenu, appID, accumulator)[1]['id'])

        action = menu_data.get('action', '')
        action = action and action.split(',')
        menuID = menu_data.get('id') or 'root'
        menu = {
            'id': menuID,
            'appID': appID,
            'name': menu_data['name'],
            'children': children,
            'actionModel': action[0] if action else False,
            'actionID': int(action[1]) if action else False,
            'xmlid': menu_data.get('xmlid', '')
        }
        accumulator[menuID] = menu
        return accumulator, menu
