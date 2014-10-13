# -*- coding: utf-8 -*-
from openerp.osv import osv,fields
from openerp.http import request

from lxml import etree

from openerp import tools
from openerp.osv import osv, fields


class ViewVersion(osv.Model):
    _inherit = "ir.ui.view"
    
    _columns = {
        'snapshot_id' : fields.many2one('website_version.snapshot',ondelete='cascade', string="Snapshot_id"),
    }

    def write(self, cr, uid, ids, vals, context=None):
        if context is None:
            context = {}
        try:
            iter(ids)
        except:
            ids=[ids]
        
        snapshot_id=context.get('snapshot_id')

        if snapshot_id and not context.get('mykey'):
            ctx = dict(context, mykey=True)
            snap = self.pool['website_version.snapshot']
            snapshot=snap.browse(cr, uid, [snapshot_id], context=ctx)[0]
            website_id=snapshot.website_id.id
            snap_ids = []
            for current in self.browse(cr, uid, ids, context=context):
                #check if current is in snapshot
                if current.snapshot_id.id == snapshot_id:
                    snap_ids.append(current.id)
                else:
                    new_id = self.search(cr, uid, [('website_id', '=', website_id),('snapshot_id', '=', snapshot_id), ('key', '=', current.key)], context=context)
                    if new_id:
                        snap_ids.append(new_id[0])
                    else:
                        copy_id=self.copy(cr,uid, current.id,{'snapshot_id':snapshot_id, 'website_id':website_id},context=ctx)
                        snap_ids.append(copy_id)
            super(ViewVersion, self).write(cr, uid, snap_ids, vals, context=ctx)
        else:
            ctx = dict(context, mykey=True)
            super(ViewVersion, self).write(cr, uid, ids, vals, context=context)
    
    #To make a snapshot of a snapshot
    def copy_snapshot(self,cr, uid, snapshot_id,new_snapshot_id, context=None):
        if context is None:
            context = {}
        ctx = dict(context, mykey=True)
        snap = self.pool['website_version.snapshot']
        snapshot=snap.browse(cr, uid, [snapshot_id],ctx)[0]
        for view in snapshot.view_ids:
            copy_id=self.copy(cr,uid,view.id,{'snapshot_id':new_snapshot_id},context=ctx)

    #To publish a master view
    def action_publish(self,cr,uid,ids,context=None):
        if context is None:
            context = {}
        ctx = dict(context, mykey=True)
        view_id = context.get('active_id')
        view = self.browse(cr, uid, [view_id],context)[0]
        key = view.key
        if view.website_id and view.snapshot_id:
            #from pudb import set_trace; set_trace()
            master_id = self.search(cr, uid, [('key','=',key),('snapshot_id', '=', False),('website_id', '=', view.website_id.id)],context=context)
            if master_id:
                self.unlink(cr, uid, master_id, context=context)
            self.copy(cr, uid, view_id, {'key':key, 'website_id': view.website_id.id, 'snapshot_id': None}, context=context)

    _read_template_cache = dict(accepted_keys=('lang', 'inherit_branding', 'editable', 'translatable', 'website_id','snapshot_id'))

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

    @tools.ormcache(size=0)
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
        self.get_view_id.clear_cache(self)


    def get_inheriting_views_arch(self, cr, uid, view_id, model, context=None):
        arch = super(ViewVersion, self).get_inheriting_views_arch(cr, uid, view_id, model, context=context)
        v = self.browse(cr, uid, [view_id],context)[0]
        if context and context.get('website_id') and v.type == 'qweb':
            # if v.key == 'website.footer_custom':
            #     from pudb import set_trace; set_trace()
            dico = {}
            view_arch = dict([(v, a) for a, v in arch])
            keys = self.read(cr, uid, view_arch.keys(), ['key','snapshot_id','website_id'], context)
            for k in keys:
                if context.get('snapshot_id'):
                    if k['snapshot_id'] and k['snapshot_id'][0] == context.get('snapshot_id'):
                        dico[k['key']] = k['id']
                    elif k['snapshot_id'] == False and k['website_id'] and k['website_id'][0] == context.get('website_id') and not dico.get(k['key']):
                        dico[k['key']] = k['id']
                    elif k['snapshot_id'] == False and k['website_id'] == False and not dico.get(k['key']):
                        dico[k['key']] = k['id']
                else:
                    if k['snapshot_id'] == False and k['website_id'] and k['website_id'][0] == context.get('website_id'):
                        dico[k['key']] = k['id']
                    elif k['snapshot_id'] == False and k['website_id'] == False and not dico.get(k['key']):
                        dico[k['key']] = k['id']
            result = []
            for x in arch:
                if x[1] in dico.values():
                    result.append(x)
            # if len(result)>0 and len(arch)>0:
            #     from pudb import set_trace; set_trace()
            return result
        return arch 

        
                