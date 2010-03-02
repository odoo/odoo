from osv import fields, osv
from service import web_services
import time
import wizard
import pooler

class wiki_wiki_help_open(osv.osv_memory):
    _name = "wiki.wiki.help.open"
    _description = "Basic Wiki Editing"
    _columns = {
    }
    def _open_wiki_page(self, cr, uid, ids, context):
        """ Opens Wiki Page for Editing"""
        pages = self.pool.get('wiki.wiki').search(cr, uid, [('name', '=', 'Basic Wiki Editing')])

        value = {
            'view_type': 'form', 
            'view_mode': 'form,tree', 
            'res_model': 'wiki.wiki', 
            'view_id': False, 
            'res_id': pages[0], 
            'type': 'ir.actions.act_window', 
        }

        return value

wiki_wiki_help_open()
