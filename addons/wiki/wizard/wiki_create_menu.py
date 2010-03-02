from osv import fields, osv
from service import web_services
import time
import wizard
import pooler

class wiki_create_menu(osv.osv_memory):
    _name = "wiki.create.menu"
    _description = "Wizard Create Menu"
    _columns = {
        'menu_name': fields.char('Menu Name', size=256, select=True, required=True), 
        'menu_parent_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True), 
        'page': fields.many2one('wiki.wiki', 'Group Home Page'), 
    }

    def wiki_menu_create(self, cr, uid, ids, context):
        """ Create Menu On the base of Group id and Action id """

        for group in self.pool.get('wiki.groups').browse(cr, uid, ids):
            for menu in self.pool.get('wiki.create.menu').browse(cr, uid, ids):

                mod_obj = self.pool.get('ir.model.data')
                action_id = mod_obj._get_id(cr, uid, 'wiki', 'action_view_wiki_wiki_page_open')
                menu_id = self.pool.get('ir.ui.menu').create(cr, uid, {
                'name': menu.menu_name, 
                'parent_id': menu.menu_parent_id.id, 
                'icon': 'STOCK_DIALOG_QUESTION', 
                'action': 'ir.actions.act_window,'+ str(action_id)
                }, context)
                home = menu.page.id
                group_id = menu.id
                res = {
                'home': home, 
                }
                self.pool.get('wiki.groups').write(cr, uid, ids, res)
                self.pool.get('wiki.groups.link').create(cr, uid, {'group_id': group_id, 'action_id': menu_id})

                return {}


wiki_create_menu()
