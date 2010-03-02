from osv import fields, osv
from service import web_services
import time
import wizard
import pooler

class wiki_wiki_page_open(osv.osv_memory):
    _name = "wiki.wiki.page.open"
    _description = "wiz open page"
    _columns = {

    }
    def _open_wiki_page(self, cr, uid, ids, context):
        """ Opens Wiki Page of Group"""
        for group in self.pool.get('wiki.groups').browse(cr, uid, ids):

         for openpage in self.pool.get('wiki.wiki.page.open').browse(cr, uid, ids):

            value = {
                'domain': "[('group_id','=',%d)]" % (group.id), 
                'name': 'Wiki Page', 
                'view_type': 'form', 
                'view_mode': 'form,tree', 
                'res_model': 'wiki.wiki', 
                'view_id': False, 
                'type': 'ir.actions.act_window', 
        }
        if group.method == 'page':
            value['res_id'] = group.home.id
        elif group.method == 'list':
            value['view_type'] = 'form'
            value['view_mode'] = 'tree,form'
        elif group.method == 'tree':
            view_id = pool.get('ir.ui.view').search(cr, uid, [('name', '=', 'wiki.wiki.tree.childs')])
            value['view_id'] = view_id
            value['domain'] = [('group_id', '=', group.id), ('parent_id', '=', False)]
            value['view_type'] = 'tree'

        return value

wiki_wiki_page_open()
