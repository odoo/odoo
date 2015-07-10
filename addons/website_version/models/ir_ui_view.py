# -*- coding: utf-8 -*-
from lxml import etree
from openerp import tools, fields, models, api


class view(models.Model):

    _inherit = "ir.ui.view"

    version_id = fields.Many2one('website_version.version', ondelete='cascade', string="Version")

    @api.multi
    def write(self, vals):
        if self.env.context is None:
            self.env.context = {}

        version_id = self.env.context.get('version_id')
        #If you write on a shared view, your modifications will be seen on every website wich uses these view.
        #To dedicate a view for a specific website, you must create a version and publish these version.
        if version_id and not self.env.context.get('write_on_view') and not 'active' in vals:
            self.env.context = dict(self.env.context, write_on_view=True)
            version = self.env['website_version.version'].browse(version_id)
            website_id = version.website_id.id
            version_view_ids = self.env['ir.ui.view']
            for current in self:
                #check if current is in version
                if current.version_id.id == version_id:
                    version_view_ids += current
                else:
                    new_v = self.search([('website_id', '=', website_id), ('version_id', '=', version_id), ('key', '=', current.key)])
                    if new_v:
                        version_view_ids += new_v
                    else:
                        copy_v = current.copy({'version_id': version_id, 'website_id': website_id})
                        version_view_ids += copy_v
            super(view, version_view_ids).write(vals)
        else:
            self.env.context = dict(self.env.context, write_on_view=True)
            super(view, self).write(vals)

    @api.one
    def publish(self):
        #To delete and replace views which are in the website( in fact with website_id)
        master_record = self.search([('key', '=', self.key), ('version_id', '=', False), ('website_id', '=', self.website_id.id)])
        if master_record:
            master_record.unlink()
        self.copy({'version_id': None})

    #To publish a view in backend
    @api.multi
    def action_publish(self):
        self.publish()

    @api.model
    def get_view_id(self, xml_id):
        if self.env.context and 'website_id' in self.env.context and not isinstance(xml_id, (int, long)):
            domain = [('key', '=', xml_id), '|', ('website_id', '=', self.env.context['website_id']), ('website_id', '=', False)]
            if 'version_id' in self.env.context:
                domain += ['|', ('version_id', '=', self.env.context['version_id']), ('version_id', '=', False)]
            xml_id = self.search(domain, order='website_id,version_id', limit=1).id
        else:
            xml_id = super(view, self).get_view_id(xml_id)
        return xml_id

    @tools.ormcache_context('uid', 'view_id',
        keys=('lang', 'inherit_branding', 'editable', 'translatable', 'edit_translations', 'website_id', 'version_id'))
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

    #To take the right inheriting views
    @api.model
    def get_inheriting_views_arch(self, view_id, model):
        arch = super(view, self).get_inheriting_views_arch(view_id, model)
        vw = self.browse(view_id)
        if not (self.env.context and self.env.context.get('website_id') and vw.type == 'qweb'):
            return arch
        #right_ids to collect the right ids according to the key
        right_ids = {}
        priority = {}
        #To create a dico called view_arch where v(key) is the id and a the arch(value)
        view_arch = dict([(v, a) for a, v in arch])
        keys = self.browse(view_arch.keys())
        #The view to take depends of the context
        context_version_id = self.env.context.get('version_id')
        context_website_id = self.env.context.get('website_id')
        for k in keys:
            #priority:1(with context_version_id) take the view which is in the same version
            if context_version_id and k.version_id.id and k.version_id.id == context_version_id:
                right_ids[k.key] = k.id
                priority[k.key] = 3
            #priority:2(context_version_id) take the view which is just in the same website
            elif context_version_id and k.version_id.id is False and k.website_id.id and k.website_id.id == context_website_id:
                if not priority.get(k.key) or priority.get(k.key) < 3:
                    right_ids[k.key] = k.id
                    priority[k.key] = 2
            #priority:3(context_version_id) take the original view
            elif context_version_id and k.version_id.id is False and k.website_id.id is False:
                if not priority.get(k.key) or priority.get(k.key) < 2:
                    right_ids[k.key] = k.id
                    priority[k.key] = 1
            #priority:1(without context_version_id) take the view which is just in the same website
            elif not context_version_id and k.version_id.id is False and k.website_id.id and k.website_id.id == context_website_id:
                right_ids[k.key] = k.id
                priority[k.key] = 2
            #priority:2(without context_version_id) take the original view
            elif not context_version_id and k.version_id.id is False and k.website_id.id is False:
                if not priority.get(k.key) or priority.get(k.key) < 2:
                    right_ids[k.key] = k.id
                    priority[k.key] = 1
        return [x for x in arch if x[1] in right_ids.values()]
        
    #To active or desactive the right views according to the key
    def toggle(self, cr, uid, ids, context=None):
        """ Switches between enabled and disabled statuses
        """
        for view in self.browse(cr, uid, ids, context=dict(context or {}, active_test=False)):
            all_id = self.search(cr, uid, [('key', '=', view.key)], context=dict(context or {}, active_test=False))
            for v in self.browse(cr, uid, all_id, context=dict(context or {}, active_test=False)):
                v.write({'active': not v.active})

    @api.model
    def translate_qweb(self, id_, arch, lang):
        view = self.browse(id_)
        if not view.key:
            return super(view, self).translate_qweb(id_, arch, lang)
        views = self.search([('key', '=', view.key), '|',
                             ('website_id', '=', view.website_id.id), ('website_id', '=', False)])
        fallback_views = self
        for v in views:
            if v.mode == 'primary' and v.inherit_id.mode == 'primary':
                # template is `cloned` from parent view
                fallback_views += view.inherit_id
        views += fallback_views
        def translate_func(term):
            Translations = self.env['ir.translation']
            trans = Translations._get_source('website', 'view', lang, term, views.ids)
            return trans
        self._translate_qweb(arch, translate_func)
        return arch

    @api.model
    def customize_template_get(self, key, full=False, bundles=False, **kw):
        result = super(view, self).customize_template_get(key, full=full, bundles=bundles, **kw)
        check = []
        res = []
        for data in result:
            if data['name'] not in check:
                check.append(data['name'])
                res.append(data)
        return res
