# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import pytz

import simplejson
import cgi
import pooler
import tools
from osv import fields, osv
from tools.translate import _
from lxml import etree

#Application and feature chooser, this could be done by introspecting ir.modules
DEFAULT_MODULES = {
    'Customer Relationship Management' : ['crm',],
    'Sales Management' : ['sale',],
    'Project Management' : ['project',],
    'Knowledge Management' : ['document',],
    'Warehouse Management' : ['stock',],
    'Manufacturing' : ['mrp', 'procurement'],
    'Accounting & Finance' : ['account,'],
    'Purchase Management' : ['purchase,'],
    'Human Resources' : ['hr',],
    'Point of Sales' : ['pos',],
    'Marketing' : ['marketing',],
}

class base_setup_installer(osv.osv_memory):
    _name = 'base.setup.installer'

    _inherit = 'res.config.installer'

    _columns = {
        'selection' : fields.text('Selection'),
    }

    def fields_get(self, cr, uid, fields=None, context=None):
        if context is None:
            context = {}
        if fields is None:
            fields = {}

        fields = {} 
        category_proxy = self.pool.get('ir.module.category')
        domain = [('parent_id', '=', False),
                  ('name', '!=', 'Uncategorized'),
                  ('visible', '=', True)]
        category_ids = category_proxy.search(cr, uid, domain, context=context)
        for category in category_proxy.browse(cr, uid, category_ids, context=context):
            category_name = 'category_%d' % (category.id,)
            fields[category_name] = {
                'type' : 'boolean',
                'string' : category.name,
                'name' : category_name,
                'help' : category.description,
            }

        module_proxy = self.pool.get('ir.module.module')
        module_ids = module_proxy.search(cr, uid, [], context=context)
        for module in module_proxy.browse(cr, uid, module_ids, context=context):
            module_name = 'module_%d' % (module.id,)
            module_is_installed = module.state == 'installed'

            fields[module_name] = {
                'type' : 'boolean',
                'string' : module.shortdesc,
                'name' : module_name,
                'help' : module.description,
            }

        return fields

    def default_get(self, cr, uid, fields=None, context=None):
        if context is None:
            context = {}
        if fields is None:
            fields = {}

        result = {}

        if 'dont_compute_virtual_attributes' not in context:
            module_proxy = self.pool.get('ir.module.module')
            module_ids = module_proxy.search(cr, uid, [], context=context)
            for module in module_proxy.browse(cr, uid, module_ids, context=context):
                result['module_%d' % (module.id,)] = module.state == 'installed'

            cat_proxy = self.pool.get('ir.module.category')
            cat_ids = cat_proxy.search(cr, uid, [], context=context)
            for cat in cat_proxy.browse(cr, uid, cat_ids, context=context):
                m = DEFAULT_MODULES.get(cat.name,[])
                r = module_proxy.search(cr, uid, [('state','=','installed'),('name','in',m)])
                result['category_%d' % (cat.id,)] = bool(r)

        return result

    def fields_view_get(self, cr, uid, view_id=None, view_type='from', context=None, toolbar=False, submenu=False):
        def in_extended_view_group(cr, uid, context=None):
            try:
                model, group_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'group_extended')
            except ValueError:
                return False
            return group_id in self.pool.get('res.users').read(cr, uid, uid, ['groups_id'], context=context)['groups_id']

        result = super(base_setup_installer, self).fields_view_get(cr, uid, view_id, view_type, context, toolbar, submenu)

        module_category_proxy = self.pool.get('ir.module.category')
        domain = [('parent_id', '=', False),
                  ('name', '!=', 'Uncategorized'),
                  ('visible', '=', True)]
        module_category_ids = module_category_proxy.search(cr, uid, domain, context=context, order='sequence asc')

        arch = ['<form string="%s">' % _('Automatic Base Setup')]
        arch.append('<separator string="%s" colspan="4" />' % _('Install Applications'))
        module_proxy = self.pool.get('ir.module.module')

        extended_view = in_extended_view_group(cr, uid, context=context)

        for module_category in module_category_proxy.browse(cr, uid, module_category_ids, context=context):
            domain = [('category_id', '=', module_category.id)]
            if not extended_view:
                domain.append(('complexity', '!=', 'expert'))

            default_modules = DEFAULT_MODULES.get(module_category.name, False)
            if default_modules:
                domain.append(('name', 'not in', default_modules))

            modules = module_proxy.browse(cr, uid, module_proxy.search(cr, uid, domain, context=context), context=context)
            if not modules:
                continue

            readonly = any(module.state == 'installed' for module in modules)

            attributes = {
                'name' : 'category_%d' % (module_category.id,),
                'on_change' : 'on_change_%s_%d(category_%d)' % ('category', module_category.id, module_category.id,),
            }
            if readonly:
                attributes['modifiers'] = simplejson.dumps({'readonly' : True})

            arch.append("""<field %s />""" % (" ".join(["%s='%s'" % (key, value,)
                                                        for key, value in attributes.iteritems()]),))

        # Compute the module to show

        for module_category in module_category_proxy.browse(cr, uid, module_category_ids, context=context):
            domain = [('category_id', '=', module_category.id)]

            if not extended_view:
                domain.append(('complexity', '!=', 'expert'))

            default_modules = DEFAULT_MODULES.get(module_category.name, False)
            if default_modules:
                domain.append(('name', 'not in', default_modules))

            modules = module_proxy.browse(cr, uid, module_proxy.search(cr, uid, domain, context=context), context=context)

            if not modules:
                continue

            modifiers = {
                'invisible' : [('category_%d' % (module_category.id), '=', False)],
            }
            module_modifiers = dict(modifiers)

            arch.append("""<separator string="%s Features" colspan="4" modifiers='%s'/>""" % (
                cgi.escape(module_category.name),
                simplejson.dumps(modifiers))
            )

            for module in modules:
                #module_modifiers['readonly'] = module.state == 'installed'

                arch.append("""<field name="module_%d" modifiers='%s' />""" % (
                    module.id,
                    simplejson.dumps(module_modifiers))
                )

        arch.append(
            '<separator colspan="4" />'
            '<group colspan="4" col="2">'
            '<button special="cancel" string="Cancel" icon="gtk-cancel" />'
            '<button string="Install Modules" type="object" name="apply_cb" icon="gtk-apply" />'
            '</group>'
        )

        arch.append('</form>')

        result['arch'] = ''.join(arch)
        return result

    def __getattr__(self, name):
        if name.startswith('on_change_category_'):
            def proxy(cr, uid, ids, value, context=None):
                item = 'category_%s' % name[len('on_change_category_'):]
                return self._on_change_selection(cr, uid, ids, item, value, context=context)
            return proxy
        return getattr(super(base_setup_installer, self), name)

    def _on_change_selection(self, cr, uid, ids, item, value, context=None):
        if not isinstance(item, basestring) or not value:
            return {}

        if item.startswith('category_') or item.startswith('module_'):
            object_name, identifier = item.split('_')
        else:
            return {}

        values = {
        }

        #if object_name == 'category':
        #    module_ids = self.pool.get('ir.module.module').search(cr, uid, [('category_id', '=', int(identifier))], context=context)
        #    for module_id in module_ids:
        #        values['module_%d' % module_id] = 1

        return {'value': values}

    def create(self, cr, uid, values, context=None):
        to_install = {'categories' : [], 'modules' : []}

        for key, value in values.iteritems():
            if value == 1 and (key.startswith('module_') or key.startswith('category_')):
                kind, identifier = key.split('_')
                if kind == 'category':
                    to_install['categories'].append(long(identifier))
                if kind == 'module':
                    to_install['modules'].append(long(identifier))

        values = {
            'selection' : simplejson.dumps(to_install),
        }
        context.update(dont_compute_virtual_attributes=True)
        return super(base_setup_installer, self).create(cr, uid, values, context=context)

    def apply_cb(self, cr, uid, ids, context=None):
        category_proxy = self.pool.get('ir.module.category')
        for installer in self.browse(cr, uid, ids, context=context):
            to_install = simplejson.loads(installer.selection)

            proxy = self.pool.get('ir.module.module')

            module_ids = proxy.search(cr, uid, [('id', 'in', to_install['modules'])], context=context)
            modules = set(record['name']
                          for record in proxy.read(cr, uid, module_ids, ['name'], context=context))

            category_ids = category_proxy.search(cr, uid, [('id', 'in', to_install['categories'])], context=context)
            selected_categories = set(record['name']
                                      for record in category_proxy.read(cr, uid, category_ids, ['name'], context=context))

            # FIXME: Use a workaround, but can do better
            for category_name, default_modules in DEFAULT_MODULES.iteritems():
                if category_name in selected_categories:
                    modules.update(default_modules)

            # Special Cases:
            # * project_mrp: the dependencies are sale, project, procurement, mrp_jit
            if 'sale' in modules and 'project' in modules:
                modules.add('project_mrp')

            need_update = False
            module_ids = proxy.search(cr, uid, [('name', 'in', list(modules))], context=context)
            if module_ids:
                proxy.state_update(cr, uid, module_ids, 'to install', ['uninstalled'], context=context)
                need_update = True

            category_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'base', 'module_category_link')
            while True and category_id:
                cr.execute("select id, name from ir_module_module m where category_id = %s \
                           and (select count(d.id) from ir_module_module_dependency d \
                           where d.module_id = m.id) = (select count(d.id) from \
                           ir_module_module_dependency d inner join ir_module_module m2 on d.name = m2.name \
                           where d.module_id=m.id and m2.state in %s ) and state = %s",
                          (category_id[1], ('installed', 'to install', 'to upgrade', ), 'uninstalled',))
                modules = [name for _, name in cr.fetchall()]

                module_ids = proxy.search(cr, uid, [('name', 'in', modules)], context=context)
                if not module_ids:
                    break

                proxy.state_update(cr, uid, module_ids, 'to install', ['uninstalled'], context=context)
                need_update = True

            if need_update:
                cr.commit()
                self.pool = pooler.restart_pool(cr.dbname, update_module=True)[1]

        if 'html' in context:
            return {'type' : 'ir.actions.reload'}
        else:
            return {'type' : 'ir.actions.act_window_close'}

    # TODO: To implement in this new wizard
    #def execute(self, cr, uid, ids, context=None):
    #    module_pool = self.pool.get('ir.module.module')
    #    modules_selected = []
    #    datas = self.read(cr, uid, ids, context=context)[0]
    #    for mod in datas.keys():
    #        if mod in ('id', 'progress'):
    #            continue
    #        if datas[mod] == 1:
    #            modules_selected.append(mod)

    #    module_ids = module_pool.search(cr, uid, [('name', 'in', modules_selected)], context=context)
    #    need_install = False
    #    for module in module_pool.browse(cr, uid, module_ids, context=context):
    #        if module.state == 'uninstalled':
    #            module_pool.state_update(cr, uid, [module.id], 'to install', ['uninstalled'], context)
    #            need_install = True
    #            cr.commit()
    #        elif module.state == 'installed':
    #            cr.execute("update ir_actions_todo set state='open' \
    #                                from ir_model_data as data where data.res_id = ir_actions_todo.id \
    #                                and ir_actions_todo.type='special'\
    #                                and data.model = 'ir.actions.todo' and data.module=%s", (module.name, ))
    #    if need_install:
    #        self.pool = pooler.restart_pool(cr.dbname, update_module=True)[1]
    #    return

#Migrate data from another application Conf wiz

class migrade_application_installer_modules(osv.osv_memory):
    _name = 'migrade.application.installer.modules'
    _inherit = 'res.config.installer'
    _columns = {
        'import_saleforce': fields.boolean('Import Saleforce',
            help="For Import Saleforce"),
        'import_sugarcrm': fields.boolean('Import Sugarcrm',
            help="For Import Sugarcrm"),
        'sync_google_contact': fields.boolean('Sync Google Contact',
            help="For Sync Google Contact"),
        'quickbooks_ippids': fields.boolean('Quickbooks Ippids',
            help="For Quickbooks Ippids"),
    }

class product_installer(osv.osv_memory):
    _name = 'product.installer'
    _inherit = 'res.config'
    _columns = {
        'customers': fields.selection([('create','Create'), ('import','Import')], 'Customers', size=32, required=True, help="Import or create customers"),
    }
    _defaults = {
        'customers': 'create',
    }

    def execute(self, cr, uid, ids, context=None):
        if context is None:
             context = {}
        data_obj = self.pool.get('ir.model.data')
        val = self.browse(cr, uid, ids, context=context)[0]
        if val.customers == 'create':
            id2 = data_obj._get_id(cr, uid, 'base', 'view_partner_form')
            if id2:
                id2 = data_obj.browse(cr, uid, id2, context=context).res_id
            return {
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'res.partner',
                    'views': [(id2, 'form')],
                    'type': 'ir.actions.act_window',
                    'target': 'current',
                    'nodestroy':False,
                }
        if val.customers == 'import':
            return {'type': 'ir.actions.act_window'}

# Define users preferences for new users (ir.values)

def _lang_get(self, cr, uid, context=None):
    obj = self.pool.get('res.lang')
    ids = obj.search(cr, uid, [('translatable','=',True)])
    res = obj.read(cr, uid, ids, ['code', 'name'], context=context)
    res = [(r['code'], r['name']) for r in res]
    return res

def _tz_get(self,cr,uid, context=None):
    return [(x, x) for x in pytz.all_timezones]

class user_preferences_config(osv.osv_memory):
    _name = 'user.preferences.config'
    _inherit = 'res.config'
    _columns = {
        'context_tz': fields.selection(_tz_get,  'Timezone', size=64,
            help="Set default for new user's timezone, used to perform timezone conversions "
                 "between the server and the client."),
        'context_lang': fields.selection(_lang_get, 'Language', required=True,
            help="Sets default language for the all user interface, when UI "
                "translations are available. If you want to Add new Language, you can add it from 'Load an Official Translation' wizard  from 'Administration' menu."),
        'view': fields.selection([('simple','Simplified'),
                                  ('extended','Extended')],
                                 'Interface', required=True, help= "If you use OpenERP for the first time we strongly advise you to select the simplified interface, which has less features but is easier. You can always switch later from the user preferences." ),
        'menu_tips': fields.boolean('Display Tips', help="Check out this box if you want to always display tips on each menu action"),
                                 
    }
    _defaults={
               'view' : lambda self,cr,uid,*args: self.pool.get('res.users').browse(cr, uid, uid).view or 'simple',
               'context_lang' : 'en_US',
               'menu_tips' : True
    }
    
    def default_get(self, cr, uid, fields, context=None):
        if context is None:
            context = {}
        res = super(user_preferences_config, self).default_get(cr, uid, fields, context=context)
        res_default = self.pool.get('ir.values').get(cr, uid, 'default', False, ['res.users'])
        for id, field, value in res_default:
            res.update({field: value})
        return res

    def execute(self, cr, uid, ids, context=None):
        user_obj = self.pool.get('res.users')
        user_ids = user_obj.search(cr, uid, [], context=context)
        for o in self.browse(cr, uid, ids, context=context):
            user_obj.write(cr , uid, user_ids ,{'context_tz' : o.context_tz, 'context_lang' : o.context_lang, 'view' : o.view, 'menu_tips' : o.menu_tips}, context=context)
            ir_values_obj = self.pool.get('ir.values')
            ir_values_obj.set(cr, uid, 'default', False, 'context_tz', ['res.users'], o.context_tz)
            ir_values_obj.set(cr, uid, 'default', False, 'context_lang', ['res.users'], o.context_lang)
            ir_values_obj.set(cr, uid, 'default', False, 'view', ['res.users'], o.view)
            ir_values_obj.set(cr, uid, 'default', False, 'menu_tips', ['res.users'], o.menu_tips)
        return {}

# Specify Your Terminology

class specify_partner_terminology(osv.osv_memory):
    _name = 'base.setup.terminology'
    _inherit = 'res.config'
    _columns = {
        'partner': fields.selection([
            ('Customer','Customer'),
            ('Client','Client'),
            ('Member','Member'),
            ('Patient','Patient'),
            ('Partner','Partner'),
            ('Donor','Donor'),
            ('Guest','Guest'),
            ('Tenant','Tenant')
        ], 'How do you call a Customer', required=True ),
    }
    _defaults={
        'partner' :'Customer',
    }

    def make_translations(self, cr, uid, ids, name, type, src, value, res_id=0, context=None):
        trans_obj = self.pool.get('ir.translation')
        user_obj = self.pool.get('res.users')
        context_lang = user_obj.browse(cr, uid, uid, context=context).context_lang
        existing_trans_ids = trans_obj.search(cr, uid, [('name','=',name), ('lang','=',context_lang), ('type','=',type), ('src','=',src), ('res_id','=',res_id)])
        if existing_trans_ids:
            trans_obj.write(cr, uid, existing_trans_ids, {'value': value}, context=context)
        else:
            create_id = trans_obj.create(cr, uid, {'name': name,'lang': context_lang, 'type': type, 'src': src, 'value': value , 'res_id': res_id}, context=context)
        return {}

    def execute(self, cr, uid, ids, context=None):
        def _case_insensitive_replace(ref_string, src, value):
            import re
            pattern = re.compile(src, re.IGNORECASE)
            return pattern.sub(_(value), _(ref_string))
        trans_obj = self.pool.get('ir.translation')
        fields_obj = self.pool.get('ir.model.fields')
        menu_obj = self.pool.get('ir.ui.menu')
        act_window_obj = self.pool.get('ir.actions.act_window')
        for o in self.browse(cr, uid, ids, context=context):
            #translate label of field
            field_ids = fields_obj.search(cr, uid, [('field_description','ilike','Customer')])
            for f_id in fields_obj.browse(cr ,uid, field_ids, context=context):
                field_ref = f_id.model_id.model + ',' + f_id.name
                self.make_translations(cr, uid, ids, field_ref, 'field', f_id.field_description, _case_insensitive_replace(f_id.field_description,'Customer',o.partner), context=context)
            #translate help tooltip of field
            for obj in self.pool.models.values():
                for field_name, field_rec in obj._columns.items():
                    if field_rec.help.lower().count('customer'):
                        field_ref = obj._name + ',' + field_name
                        self.make_translations(cr, uid, ids, field_ref, 'help', field_rec.help, _case_insensitive_replace(field_rec.help,'Customer',o.partner), context=context)
            #translate menuitems
            menu_ids = menu_obj.search(cr,uid, [('name','ilike','Customer')])
            for m_id in menu_obj.browse(cr, uid, menu_ids, context=context):
                menu_name = m_id.name
                menu_ref = 'ir.ui.menu' + ',' + 'name'
                self.make_translations(cr, uid, ids, menu_ref, 'model', menu_name, _case_insensitive_replace(menu_name,'Customer',o.partner), res_id=m_id.id, context=context)
            #translate act window name
            act_window_ids = act_window_obj.search(cr, uid, [('name','ilike','Customer')])
            for act_id in act_window_obj.browse(cr ,uid, act_window_ids, context=context):
                act_ref = 'ir.actions.act_window' + ',' + 'name'
                self.make_translations(cr, uid, ids, act_ref, 'model', act_id.name, _case_insensitive_replace(act_id.name,'Customer',o.partner), res_id=act_id.id, context=context)
            #translate act window tooltips
            act_window_ids = act_window_obj.search(cr, uid, [('help','ilike','Customer')])
            for act_id in act_window_obj.browse(cr ,uid, act_window_ids, context=context):
                act_ref = 'ir.actions.act_window' + ',' + 'help'
                self.make_translations(cr, uid, ids, act_ref, 'model', act_id.help, _case_insensitive_replace(act_id.help,'Customer',o.partner), res_id=act_id.id, context=context)
        return {}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
