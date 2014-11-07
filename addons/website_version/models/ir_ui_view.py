# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
from openerp.http import request

from lxml import etree

from openerp import tools
from openerp.osv import osv, fields


class view(osv.Model):
    _inherit = "ir.ui.view"
    
    _columns = {
        'version_id' : fields.many2one('website_version.version',ondelete='cascade', string="version_id"),
    }

    def write(self, cr, uid, ids, vals, toggle=False, context=None):
        if context is None:
            context = {}
        try:
            iter(ids)
        except:
            ids=[ids]
        
        version_id=context.get('version_id')
        #toggle is true when changing active field 
        if version_id and not context.get('mykey') and not toggle:
            ctx = dict(context, mykey=True)
            snap = self.pool['website_version.version']
            version=snap.browse(cr, uid, [version_id], context=ctx)[0]
            website_id=version.website_id.id
            version_view_ids = []
            for current in self.browse(cr, uid, ids, context=context):
                #check if current is in version
                if current.version_id.id == version_id:
                    version_view_ids.append(current.id)
                else:
                    new_id = self.search(cr, uid, [('website_id', '=', website_id),('version_id', '=', version_id), ('key', '=', current.key)], context=context)
                    if new_id:
                        version_view_ids.append(new_id[0])
                    else:
                        copy_id=self.copy(cr,uid, current.id,{'version_id':version_id, 'website_id':website_id},context=ctx)
                        version_view_ids.append(copy_id)
            super(view, self).write(cr, uid, version_view_ids, vals, context=ctx)
        else:
            ctx = dict(context, mykey=True)
            super(view, self).write(cr, uid, ids, vals, context=context)
    
    #To make a version of a version
    def copy_version(self,cr, uid, version_id,new_version_id, context=None):
        if context is None:
            context = {}
        ctx = dict(context, mykey=True)
        snap = self.pool['website_version.version']
        version=snap.browse(cr, uid, [version_id],ctx)[0]
        for view in version.view_ids:
            copy_id=self.copy(cr,uid,view.id,{'version_id':new_version_id},context=ctx)

    #To publish a view
    def action_publish(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        ctx = dict(context, mykey=True)
        view_id = context.get('active_id')
        view = self.browse(cr, uid, [view_id],context)[0]
        key = view.key
        #To check if the view is in a version
        if view.website_id and view.version_id:
            master_id = self.search(cr, uid, [('key','=',key),('version_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
            if master_id:
                self.unlink(cr, uid, master_id, context=context)
            self.copy(cr, uid, view_id, {'key':key, 'website_id': view.website_id.id, 'version_id': None}, context=context)

    def get_view_id(self, cr, uid, xml_id, context=None):
        if context and 'website_id' in context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', context['website_id']), ('website_id', '=', False)]
            [xml_id] = self.search(cr, uid, domain, order='website_id', limit=1, context=context)
        else:
            xml_id = super(view, self).get_view_id(cr, uid, xml_id, context=context)
        return xml_id


    _read_template_cache = dict(accepted_keys=('lang', 'inherit_branding', 'editable', 'translatable', 'website_id','version_id'))

    @tools.ormcache_context(**_read_template_cache)
    def _read_template(self, cr, uid, view_id, context=None):
        arch = self.read_combined(cr, uid, view_id, fields=['arch'], context=context)['arch']
        arch_tree = etree.fromstring(arch)

        if 'lang' in context:
            arch_tree = self.translate_qweb(cr, uid, view_id, arch_tree, context['lang'], context)

        self.distribute_branding(arch_tree)
        root = etree.Element('templates')
        root.append(arch_tree)
        arch = etree.tostring(root, encoding='utf-8', xml_declaration=True)
        return arch

    #@tools.ormcache(size=0)
    def read_template(self, cr, uid, xml_id, context=None):
        if isinstance(xml_id, (int, long)):
            view_id = xml_id
        else:
            if '.' not in xml_id:
                raise ValueError('Invalid template id: %r' % (xml_id,))
            view_id = self.get_view_id(cr, uid, xml_id, context=context)
        return self._read_template(cr, uid, view_id, context=context)

    def clear_cache(self):
        self._read_template.clear_cache(self)
        #self.get_view_id.clear_cache(self)

    #To take the right inheriting views
    def get_inheriting_views_arch(self, cr, uid, view_id, model, context=None):
        arch = super(view, self).get_inheriting_views_arch(cr, uid, view_id, model, context=context)
        v = self.browse(cr, uid, [view_id],context)[0]
        if not (context and context.get('website_id') and v.type == 'qweb'):
            return arch
        #right_ids to collect the right ids according to the key
        right_ids = {}
        priority = {}
        #To create a dico called view_arch where v(key) is the id and a the arch(value)
        view_arch = dict([(v, a) for a, v in arch])
        keys = self.read(cr, uid, view_arch.keys(), ['key','version_id','website_id'], context)
        for k in keys:
            #The view to take depends of the context
            if context.get('version_id'):
                #priority:1 take the view which is in the same version
                if k['version_id'] and k['version_id'][0] == context.get('version_id'):
                    right_ids[k['key']] = k['id']
                    priority[k['key']] = 3
                #priority:2 take the view which is just in the same website
                elif k['version_id'] == False and k['website_id'] and k['website_id'][0] == context.get('website_id'):
                    if not priority.get(k['key']) or priority.get(k['key']) < 3:
                        right_ids[k['key']] = k['id']
                        priority[k['key']] = 2
                #priority:3 take the original view
                elif k['version_id'] == False and k['website_id'] == False:
                    if not priority.get(k['key']) or priority.get(k['key']) < 2:
                        right_ids[k['key']] = k['id']
                        priority[k['key']] = 1
            else:
                if k['version_id'] == False and k['website_id'] and k['website_id'][0] == context.get('website_id'):
                    right_ids[k['key']] = k['id']
                    priority[k['key']] = 2
                elif k['version_id'] == False and k['website_id'] == False:
                    if not priority.get(k['key']) or priority.get(k['key']) < 2:
                        right_ids[k['key']] = k['id']
                        priority[k['key']] = 1
        return [x for x in arch if x[1] in right_ids.values()]
        

    #To active or desactive the right views according to the key
    def toggle(self, cr, uid, ids, context=None):
        """ Switches between enabled and disabled statuses
        """
        for view in self.browse(cr, uid, ids, context=dict(context or {}, active_test=False)):
            all_id = self.search(cr, uid, [('key','=',view.key)], context=dict(context or {}, active_test=False))
            for v in self.browse(cr, uid, all_id, context=dict(context or {}, active_test=False)):
                v.write({'active': not v.active}, toggle=True)


        
                