# -*- coding: utf-8 -*-

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict
import logging
import re
import time
import types

import openerp
from openerp import SUPERUSER_ID
from openerp import models, tools, api
from openerp.modules.registry import RegistryManager
from openerp.osv import fields, osv
from openerp.osv.orm import BaseModel, Model, MAGIC_COLUMNS
from openerp.exceptions import UserError, AccessError
from openerp.tools import config
from openerp.tools.safe_eval import safe_eval as eval
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

MODULE_UNINSTALL_FLAG = '_force_unlink'

def _get_fields_type(self, cr, uid, context=None):
    # Avoid too many nested `if`s below, as RedHat's Python 2.6
    # break on it. See bug 939653.
    return sorted([(k,k) for k,v in fields.__dict__.iteritems()
                      if type(v) == types.TypeType and \
                         issubclass(v, fields._column) and \
                         v != fields._column and \
                         not v._deprecated and \
                         not issubclass(v, fields.function)])

def _in_modules(self, cr, uid, ids, field_name, arg, context=None):
    #pseudo-method used by fields.function in ir.model/ir.model.fields
    module_pool = self.pool["ir.module.module"]
    installed_module_ids = module_pool.search(cr, uid, [('state','=','installed')])
    installed_module_names = module_pool.read(cr, uid, installed_module_ids, ['name'], context=context)
    installed_modules = set(x['name'] for x in installed_module_names)

    result = {}
    xml_ids = osv.osv._get_xml_ids(self, cr, uid, ids)
    for k,v in xml_ids.iteritems():
        result[k] = ', '.join(sorted(installed_modules & set(xml_id.split('.')[0] for xml_id in v)))
    return result

class unknown(models.AbstractModel):
    """
    Abstract model used as a substitute for relational fields with an unknown
    comodel.
    """
    _name = '_unknown'

class ir_model(osv.osv):
    _name = 'ir.model'
    _description = "Models"
    _order = 'model'

    def _view_ids(self, cr, uid, ids, field_name, arg, context=None):
        models = self.browse(cr, uid, ids)
        res = {}
        for model in models:
            res[model.id] = self.pool["ir.ui.view"].search(cr, uid, [('model', '=', model.model)])
        return res

    def _inherited_models(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        for model in self.browse(cr, uid, ids, context=context):
            res[model.id] = []
            inherited_models = [model_name for model_name in self.pool[model.model]._inherits]
            if inherited_models:
                res[model.id] = self.search(cr, uid, [('model', 'in', inherited_models)], context=context)
        return res

    _columns = {
        'name': fields.char('Model Description', translate=True, required=True),
        'model': fields.char('Model', required=True, select=1),
        'info': fields.text('Information'),
        'field_id': fields.one2many('ir.model.fields', 'model_id', 'Fields', required=True, copy=True),
        'inherited_model_ids': fields.function(_inherited_models, type="many2many", obj="ir.model", string="Inherited models",
            help="The list of models that extends the current model."),
        'state': fields.selection([('manual','Custom Object'),('base','Base Object')],'Type', readonly=True),
        'access_ids': fields.one2many('ir.model.access', 'model_id', 'Access'),
        'transient': fields.boolean(string="Transient Model"),
        'modules': fields.function(_in_modules, type='char', string='In Apps', help='List of modules in which the object is defined or inherited'),
        'view_ids': fields.function(_view_ids, type='one2many', obj='ir.ui.view', string='Views'),
    }

    _defaults = {
        'model': 'x_',
        'state': 'manual',
    }

    def _check_model_name(self, cr, uid, ids, context=None):
        for model in self.browse(cr, uid, ids, context=context):
            if model.state=='manual':
                if not model.model.startswith('x_'):
                    return False
            if not re.match('^[a-z_A-Z0-9.]+$',model.model):
                return False
        return True

    def _model_name_msg(self, cr, uid, ids, context=None):
        return _('The Object name must start with x_ and not contain any special character !')

    _constraints = [
        (_check_model_name, _model_name_msg, ['model']),
    ]
    _sql_constraints = [
        ('obj_name_uniq', 'unique (model)', 'Each model must be unique!'),
    ]

    # overridden to allow searching both on model name (model field)
    # and model description (name field)
    def _name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=100, name_get_uid=None):
        if args is None:
            args = []
        domain = args + ['|', ('model', operator, name), ('name', operator, name)]
        return self.name_get(cr, name_get_uid or uid,
                             super(ir_model, self).search(cr, uid, domain, limit=limit, context=context),
                             context=context)

    def _drop_table(self, cr, uid, ids, context=None):
        for model in self.browse(cr, uid, ids, context):
            model_pool = self.pool[model.model]
            cr.execute('select relkind from pg_class where relname=%s', (model_pool._table,))
            result = cr.fetchone()
            if result and result[0] == 'v':
                cr.execute('DROP view %s' % (model_pool._table,))
            elif result and result[0] == 'r':
                cr.execute('DROP TABLE %s CASCADE' % (model_pool._table,))
        return True

    def unlink(self, cr, user, ids, context=None):
        # Prevent manual deletion of module tables
        if context is None: context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not context.get(MODULE_UNINSTALL_FLAG):
            for model in self.browse(cr, user, ids, context):
                if model.state != 'manual':
                    raise UserError(_("Model '%s' contains module data and cannot be removed!") % (model.name,))
                # prevent screwing up fields that depend on these models' fields
                model.field_id._prepare_update()

        self._drop_table(cr, user, ids, context)
        res = super(ir_model, self).unlink(cr, user, ids, context)
        if not context.get(MODULE_UNINSTALL_FLAG):
            # only reload pool for normal unlink. For module uninstall the
            # reload is done independently in openerp.modules.loading
            cr.commit() # must be committed before reloading registry in new cursor
            api.Environment.reset()
            RegistryManager.new(cr.dbname)
            RegistryManager.signal_registry_change(cr.dbname)

        return res

    def write(self, cr, user, ids, vals, context=None):
        if context:
            context = dict(context)
            context.pop('__last_update', None)
        if 'model' in vals:
            raise UserError(_('Field "Model" cannot be modified on models.'))
        if 'state' in vals:
            raise UserError(_('Field "Type" cannot be modified on models.'))
        if 'transient' in vals:
            raise UserError(_('Field "Transient Model" cannot be modified on models.'))
        # Filter out operations 4 link from field id, because openerp-web
        # always write (4,id,False) even for non dirty items
        if 'field_id' in vals:
            vals['field_id'] = [op for op in vals['field_id'] if op[0] != 4]
        return super(ir_model,self).write(cr, user, ids, vals, context)

    def create(self, cr, user, vals, context=None):
        if  context is None:
            context = {}
        res = super(ir_model,self).create(cr, user, vals, context)
        if vals.get('state','manual')=='manual':
            # setup models; this automatically adds model in registry
            self.pool.setup_models(cr, partial=(not self.pool.ready))
            # update database schema
            model = self.pool[vals['model']]
            ctx = dict(context, update_custom_fields=True)
            model._auto_init(cr, ctx)
            model._auto_end(cr, ctx) # actually create FKs!
            RegistryManager.signal_registry_change(cr.dbname)
        return res

    def instanciate(self, cr, user, model, transient, context=None):
        if isinstance(model, unicode):
            model = model.encode('utf-8')

        class CustomModel(models.Model):
            _name = model
            _module = False
            _custom = True
            _transient = bool(transient)

        CustomModel._build_model(self.pool, cr)

class ir_model_fields(osv.osv):
    _name = 'ir.model.fields'
    _description = "Fields"
    _rec_name = 'field_description'

    _columns = {
        'name': fields.char('Field Name', required=True, select=1),
        'complete_name': fields.char('Complete Name', select=1),
        'model': fields.char('Object Name', required=True, select=1,
            help="The technical name of the model this field belongs to"),
        'relation': fields.char('Object Relation',
            help="For relationship fields, the technical name of the target model"),
        'relation_field': fields.char('Relation Field',
            help="For one2many fields, the field on the target model that implement the opposite many2one relationship"),
        'model_id': fields.many2one('ir.model', 'Model', required=True, select=True, ondelete='cascade',
            help="The model this field belongs to"),
        'field_description': fields.char('Field Label', required=True, translate=True),
        'help': fields.text('Field Help', translate=True),
        'ttype': fields.selection(_get_fields_type, 'Field Type', required=True),
        'selection': fields.char('Selection Options', help="List of options for a selection field, "
            "specified as a Python expression defining a list of (key, label) pairs. "
            "For example: [('blue','Blue'),('yellow','Yellow')]"),
        'copy': fields.boolean('Copied', help="Whether the value is copied when duplicating a record."),
        'related': fields.char('Related Field', help="The corresponding related field, if any. This must be a dot-separated list of field names."),
        'required': fields.boolean('Required'),
        'readonly': fields.boolean('Readonly'),
        'index': fields.boolean('Indexed'),
        'translate': fields.boolean('Translatable', help="Whether values for this field can be translated (enables the translation mechanism for that field)"),
        'size': fields.integer('Size'),
        'state': fields.selection([('manual','Custom Field'),('base','Base Field')],'Type', required=True, readonly=True, select=1),
        'on_delete': fields.selection([('cascade', 'Cascade'), ('set null', 'Set NULL'), ('restrict', 'Restrict')],
                                      'On Delete', help='On delete property for many2one fields'),
        'domain': fields.char('Domain', help="The optional domain to restrict possible values for relationship fields, "
            "specified as a Python expression defining a list of triplets. "
            "For example: [('color','=','red')]"),
        'groups': fields.many2many('res.groups', 'ir_model_fields_group_rel', 'field_id', 'group_id', 'Groups'),
        'selectable': fields.boolean('Selectable'),
        'modules': fields.function(_in_modules, type='char', string='In Apps', help='List of modules in which the field is defined'),
        'serialization_field_id': fields.many2one('ir.model.fields', 'Serialization Field', domain = "[('ttype','=','serialized')]",
                                                  ondelete='cascade', help="If set, this field will be stored in the sparse "
                                                                           "structure of the serialization field, instead "
                                                                           "of having its own database column. This cannot be "
                                                                           "changed after creation."),
        'relation_table': fields.char("Relation Table", help="Used for custom many2many fields to define a custom relation table name"),
        'column1': fields.char("Column 1", help="Column referring to the record in the model table"),
        'column2': fields.char("Column 2", help="Column referring to the record in the comodel table"),
        'compute': fields.text("Compute", help="Code to compute the value of the field.\n"
                        "Iterate on the recordset 'self' and assign the field's value:\n\n"
                        "    for record in self:\n"
                        "        record['size'] = len(record.name)\n\n"
                        "Modules time, datetime, dateutil are available."),
        'depends': fields.char("Dependencies", help="Dependencies of compute method; "
                        "a list of comma-separated field names, like\n\n"
                        "    name, partner_id.name"),
    }
    _rec_name='field_description'
    _defaults = {
        'selection': "",
        'domain': "[]",
        'name': 'x_',
        'state': 'manual',
        'on_delete': 'set null',
        'field_description': '',
        'selectable': 1,
    }
    _order = "name"

    def _check_selection(self, cr, uid, selection, context=None):
        try:
            selection_list = eval(selection)
        except Exception:
            _logger.info('Invalid selection list definition for fields.selection', exc_info=True)
            raise UserError(_("The Selection Options expression is not a valid Pythonic expression."
                                "Please provide an expression in the [('key','Label'), ...] format."))

        check = True
        if not (isinstance(selection_list, list) and selection_list):
            check = False
        else:
            for item in selection_list:
                if not (isinstance(item, (tuple,list)) and len(item) == 2):
                    check = False
                    break

        if not check:
                raise UserError(_("The Selection Options expression is must be in the [('key','Label'), ...] format!"))
        return True

    def _size_gt_zero_msg(self, cr, user, ids, context=None):
        return _('Size of the field can never be less than 0 !')

    _sql_constraints = [
        ('size_gt_zero', 'CHECK (size>=0)',_size_gt_zero_msg ),
    ]

    def _related_field(self):
        """ Return the ``Field`` instance corresponding to ``self.related``. """
        names = self.related.split(".")
        last = len(names) - 1
        model = self.env[self.model or self.model_id.model]
        for index, name in enumerate(names):
            field = model._fields.get(name)
            if field is None:
                raise UserError(_("Unknown field name '%s' in related field '%s'") % (name, self.related))
            if index < last and not field.relational:
                raise UserError(_("Non-relational field name '%s' in related field '%s'") % (name, self.related))
            model = model[name]
        return field

    @api.one
    @api.constrains('related')
    def _check_related(self):
        if self.state == 'manual' and self.related:
            field = self._related_field()
            if field.type != self.ttype:
                raise UserError(_("Related field '%s' does not have type '%s'") % (self.related, self.ttype))
            if field.relational and field.comodel_name != self.relation:
                raise UserError(_("Related field '%s' does not have comodel '%s'") % (self.related, self.relation))

    @api.onchange('related')
    def _onchange_related(self):
        if self.related:
            try:
                field = self._related_field()
            except UserError as e:
                return {'warning': {'title': _("Warning"), 'message': e.message}}
            self.ttype = field.type
            self.relation = field.comodel_name
            self.readonly = True
            self.copy = False

    @api.constrains('depends')
    def _check_depends(self):
        """ Check whether all fields in dependencies are valid. """
        for record in self:
            if not record.depends:
                continue
            for seq in record.depends.split(","):
                if not seq.strip():
                    raise UserError(_("Empty dependency in %r") % (record.depends))
                model = self.env[record.model]
                names = seq.strip().split(".")
                last = len(names) - 1
                for index, name in enumerate(names):
                    field = model._fields.get(name)
                    if field is None:
                        raise UserError(_("Unknown field %r in dependency %r") % (name, seq.strip()))
                    if index < last and not field.relational:
                        raise UserError(_("Non-relational field %r in dependency %r") % (name, seq.strip()))
                    model = model[name]

    @api.onchange('compute')
    def _onchange_compute(self):
        if self.compute:
            self.readonly = True
            self.copy = False

    @api.one
    @api.constrains('relation_table')
    def _check_relation_table(self):
        models.check_pg_name(self.relation_table)

    @api.model
    def _custom_many2many_names(self, model_name, comodel_name):
        """ Return default names for the table and columns of a custom many2many field. """
        rel1 = self.env[model_name]._table
        rel2 = self.env[comodel_name]._table
        table = 'x_%s_%s_rel' % tuple(sorted([rel1, rel2]))
        if rel1 == rel2:
            return (table, 'id1', 'id2')
        else:
            return (table, '%s_id' % rel1, '%s_id' % rel2)

    @api.onchange('ttype', 'model_id', 'relation')
    def _onchange_ttype(self):
        self.copy = (self.ttype != 'one2many')
        if self.ttype == 'many2many' and self.model_id and self.relation:
            names = self._custom_many2many_names(self.model_id.model, self.relation)
            self.relation_table, self.column1, self.column2 = names
        else:
            self.relation_table = False
            self.column1 = False
            self.column2 = False

    @api.onchange('relation_table')
    def _onchange_relation_table(self):
        if self.relation_table:
            # check whether other fields use the same table
            others = self.search([('ttype', '=', 'many2many'),
                                  ('relation_table', '=', self.relation_table),
                                  ('id', 'not in', self._origin.ids)])
            if others:
                for other in others:
                    if (other.model, other.relation) == (self.relation, self.model):
                        # other is a candidate inverse field
                        self.column1 = other.column2
                        self.column2 = other.column1
                        return
                return {'warning':{
                    'title': _("Warning"),
                    'message': _("The table %r if used for other, possibly incompatible fields.") % self.relation_table,
                }}

    def _drop_column(self, cr, uid, ids, context=None):
        tables_to_drop = set()

        for field in self.browse(cr, uid, ids, context):
            if field.name in MAGIC_COLUMNS:
                continue
            model = self.pool[field.model]
            cr.execute('SELECT relkind FROM pg_class WHERE relname=%s', (model._table,))
            result = cr.fetchone()
            cr.execute("""SELECT column_name FROM information_schema.columns
                          WHERE table_name=%s AND column_name=%s""",
                       (model._table, field.name))
            column_name = cr.fetchone()
            if column_name and (result and result[0] == 'r'):
                cr.execute('ALTER table "%s" DROP column "%s" cascade' % (model._table, field.name))
            if field.state == 'manual' and field.ttype == 'many2many':
                rel_name = field.relation_table or model._fields[field.name].relation
                tables_to_drop.add(rel_name)
            if field.state == 'manual':
                model._pop_field(cr, uid, field.name, context=context)

        if tables_to_drop:
            # drop the relation tables that are not used by other fields
            cr.execute("""SELECT relation_table FROM ir_model_fields
                          WHERE relation_table IN %s AND id NOT IN %s""",
                       (tuple(tables_to_drop), tuple(ids)))
            tables_to_keep = set(row[0] for row in cr.fetchall())
            for rel_name in tables_to_drop - tables_to_keep:
                cr.execute('DROP TABLE "%s"' % rel_name)

        return True

    @api.multi
    def _prepare_update(self):
        """ Check whether the fields in ``self`` may be modified or removed.
            This method prevents the modification/deletion of many2one fields
            that have an inverse one2many, for instance.
        """
        for record in self:
            model = self.env[record.model]
            field = model._fields[record.name]
            if field.type == 'many2one' and model._field_inverses.get(field):
                msg = _("The field '%s' cannot be removed because the field '%s' depends on it.")
                raise UserError(msg % (field, model._field_inverses[field][0]))

    def unlink(self, cr, user, ids, context=None):
        # Prevent manual deletion of module columns
        if context is None: context = {}
        if isinstance(ids, (int, long)):
            ids = [ids]
        if not context.get(MODULE_UNINSTALL_FLAG) and \
                any(field.state != 'manual' for field in self.browse(cr, user, ids, context)):
            raise UserError(_("This column contains module data and cannot be removed!"))

        # prevent screwing up fields that depend on these fields
        self.browse(cr, user, ids, context=context)._prepare_update()

        self._drop_column(cr, user, ids, context)
        res = super(ir_model_fields, self).unlink(cr, user, ids, context)
        if not context.get(MODULE_UNINSTALL_FLAG):
            # The field we just deleted might be inherited, and the registry is
            # inconsistent in this case; therefore we reload the registry.
            cr.commit()
            api.Environment.reset()
            RegistryManager.new(cr.dbname)
            RegistryManager.signal_registry_change(cr.dbname)
        return res

    def create(self, cr, user, vals, context=None):
        if 'model_id' in vals:
            model_data = self.pool['ir.model'].browse(cr, user, vals['model_id'])
            vals['model'] = model_data.model
        if context is None:
            context = {}
        if vals.get('ttype', False) == 'selection':
            if not vals.get('selection',False):
                raise UserError(_('For selection fields, the Selection Options must be given!'))
            self._check_selection(cr, user, vals['selection'], context=context)
        res = super(ir_model_fields,self).create(cr, user, vals, context)
        if vals.get('state','manual') == 'manual':
            if not vals['name'].startswith('x_'):
                raise UserError(_("Custom fields must have a name that starts with 'x_' !"))

            if vals.get('relation',False) and not self.pool['ir.model'].search(cr, user, [('model','=',vals['relation'])]):
                raise UserError(_("Model %s does not exist!") % vals['relation'])

            if vals.get('ttype', False) == 'one2many':
                if not self.search(cr, user, [('model_id','=',vals['relation']), ('name','=',vals['relation_field']), ('ttype','=','many2one')]):
                    raise UserError(_("Many2one %s on model %s does not exist!") % (vals['relation_field'], vals['relation']))

            self.pool.clear_manual_fields()

            if vals['model'] in self.pool:
                # setup models; this re-initializes model in registry
                self.pool.setup_models(cr, partial=(not self.pool.ready))
                # update database schema
                model = self.pool[vals['model']]
                ctx = dict(context, update_custom_fields=True)
                model._auto_init(cr, ctx)
                model._auto_end(cr, ctx) # actually create FKs!
                RegistryManager.signal_registry_change(cr.dbname)

        return res

    def write(self, cr, user, ids, vals, context=None):
        if context is None:
            context = {}

        #For the moment renaming a sparse field or changing the storing system is not allowed. This may be done later
        if 'serialization_field_id' in vals or 'name' in vals:
            for field in self.browse(cr, user, ids, context=context):
                if 'serialization_field_id' in vals and field.serialization_field_id.id != vals['serialization_field_id']:
                    raise UserError(_('Changing the storing system for field "%s" is not allowed.') % field.name)
                if field.serialization_field_id and (field.name != vals['name']):
                    raise UserError(_('Renaming sparse field "%s" is not allowed') % field.name)

        # if set, *one* column can be renamed here
        column_rename = None

        # names of the models to patch
        patched_models = set()

        if vals and ids:
            # check selection if given
            if vals.get('selection'):
                self._check_selection(cr, user, vals['selection'], context=context)

            for item in self.browse(cr, user, ids, context=context):
                if item.state != 'manual':
                    raise UserError(_('Properties of base fields cannot be altered in this manner! '
                                        'Please modify them through Python code, '
                                        'preferably through a custom addon!'))

                if vals.get('model_id', item.model_id.id) != item.model_id.id:
                    raise UserError(_("Changing the model of a field is forbidden!"))

                if vals.get('ttype', item.ttype) != item.ttype:
                    raise UserError(_("Changing the type of a field is not yet supported. "
                                      "Please drop it and create it again!"))

                obj = self.pool.get(item.model)
                field = getattr(obj, '_fields', {}).get(item.name)

                if vals.get('name', item.name) != item.name:
                    # We need to rename the column
                    item._prepare_update()
                    if column_rename:
                        raise UserError(_('Can only rename one field at a time!'))
                    if vals['name'] in obj._fields:
                        raise UserError(_('Cannot rename field to %s, because that field already exists!') % vals['name'])
                    if vals.get('state', 'manual') == 'manual' and not vals['name'].startswith('x_'):
                        raise UserError(_('New field name must still start with x_ , because it is a custom field!'))
                    if '\'' in vals['name'] or '"' in vals['name'] or ';' in vals['name']:
                        raise ValueError('Invalid character in column name')
                    column_rename = (obj._table, item.name, vals['name'], item.index)

                # We don't check the 'state', because it might come from the context
                # (thus be set for multiple fields) and will be ignored anyway.
                if obj is not None and field is not None:
                    patched_models.add(obj._name)

        # These shall never be written (modified)
        for column_name in ('model_id', 'model', 'state'):
            if column_name in vals:
                del vals[column_name]

        res = super(ir_model_fields,self).write(cr, user, ids, vals, context=context)

        self.pool.clear_manual_fields()

        if column_rename:
            # rename column in database, and its corresponding index if present
            table, oldname, newname, index = column_rename
            cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, oldname, newname))
            if index:
                cr.execute('ALTER INDEX "%s_%s_index" RENAME TO "%s_%s_index"' % (table, oldname, table, newname))

        if column_rename or patched_models:
            # setup models, this will reload all manual fields in registry
            self.pool.setup_models(cr, partial=(not self.pool.ready))

        if patched_models:
            # update the database schema of the models to patch
            ctx = dict(context, update_custom_fields=True)
            for model_name in patched_models:
                obj = self.pool[model_name]
                obj._auto_init(cr, ctx)
                obj._auto_end(cr, ctx) # actually create FKs!

        if column_rename or patched_models:
            RegistryManager.signal_registry_change(cr.dbname)

        return res

class ir_model_constraint(Model):
    """
    This model tracks PostgreSQL foreign keys and constraints used by OpenERP
    models.
    """
    _name = 'ir.model.constraint'
    _columns = {
        'name': fields.char('Constraint', required=True, select=1,
            help="PostgreSQL constraint or foreign key name."),
        'definition': fields.char('Definition', help="PostgreSQL constraint definition"),
        'model': fields.many2one('ir.model', string='Model',
            required=True, select=1),
        'module': fields.many2one('ir.module.module', string='Module',
            required=True, select=1),
        'type': fields.char('Constraint Type', required=True, size=1, select=1,
            help="Type of the constraint: `f` for a foreign key, "
                "`u` for other constraints."),
        'date_update': fields.datetime('Update Date'),
        'date_init': fields.datetime('Initialization Date')
    }

    _sql_constraints = [
        ('module_name_uniq', 'unique(name, module)',
            'Constraints with the same name are unique per module.'),
    ]

    def _module_data_uninstall(self, cr, uid, ids, context=None):
        """
        Delete PostgreSQL foreign keys and constraints tracked by this model.
        """ 

        if uid != SUPERUSER_ID and not self.pool['ir.model.access'].check_groups(cr, uid, "base.group_system"):
            raise AccessError(_('Administrator access is required to uninstall a module'))

        context = dict(context or {})

        ids_set = set(ids)
        ids.sort()
        ids.reverse()
        for data in self.browse(cr, uid, ids, context):
            model = data.model.model
            if model in self.pool:
                table = self.pool[model]._table
            else:
                table = model.replace('.', '_')
            name = openerp.tools.ustr(data.name)
            typ = data.type

            # double-check we are really going to delete all the owners of this schema element
            cr.execute("""SELECT id from ir_model_constraint where name=%s""", (data.name,))
            external_ids = [x[0] for x in cr.fetchall()]
            if set(external_ids)-ids_set:
                # as installed modules have defined this element we must not delete it!
                continue

            if typ == 'f':
                # test if FK exists on this table (it could be on a related m2m table, in which case we ignore it)
                cr.execute("""SELECT 1 from pg_constraint cs JOIN pg_class cl ON (cs.conrelid = cl.oid)
                              WHERE cs.contype=%s and cs.conname=%s and cl.relname=%s""", ('f', name, table))
                if cr.fetchone():
                    cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (table, name),)
                    _logger.info('Dropped FK CONSTRAINT %s@%s', name, model)

            if typ == 'u':
                # test if constraint exists
                cr.execute("""SELECT 1 from pg_constraint cs JOIN pg_class cl ON (cs.conrelid = cl.oid)
                              WHERE cs.contype=%s and cs.conname=%s and cl.relname=%s""", ('u', name, table))
                if cr.fetchone():
                    cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (table, name),)
                    _logger.info('Dropped CONSTRAINT %s@%s', name, model)

        self.unlink(cr, uid, ids, context)

class ir_model_relation(Model):
    """
    This model tracks PostgreSQL tables used to implement OpenERP many2many
    relations.
    """
    _name = 'ir.model.relation'
    _columns = {
        'name': fields.char('Relation Name', required=True, select=1,
            help="PostgreSQL table name implementing a many2many relation."),
        'model': fields.many2one('ir.model', string='Model',
            required=True, select=1),
        'module': fields.many2one('ir.module.module', string='Module',
            required=True, select=1),
        'date_update': fields.datetime('Update Date'),
        'date_init': fields.datetime('Initialization Date')
    }

    def _module_data_uninstall(self, cr, uid, ids, context=None):
        """
        Delete PostgreSQL many2many relations tracked by this model.
        """ 

        if uid != SUPERUSER_ID and not self.pool['ir.model.access'].check_groups(cr, uid, "base.group_system"):
            raise AccessError(_('Administrator access is required to uninstall a module'))

        ids_set = set(ids)
        to_drop_table = []
        ids.sort()
        ids.reverse()
        for data in self.browse(cr, uid, ids, context):
            model = data.model
            name = openerp.tools.ustr(data.name)

            # double-check we are really going to delete all the owners of this schema element
            cr.execute("""SELECT id from ir_model_relation where name = %s""", (data.name,))
            external_ids = [x[0] for x in cr.fetchall()]
            if set(external_ids)-ids_set:
                # as installed modules have defined this element we must not delete it!
                continue

            cr.execute("SELECT 1 FROM information_schema.tables WHERE table_name=%s", (name,))
            if cr.fetchone() and not name in to_drop_table:
                to_drop_table.append(name)

        self.unlink(cr, uid, ids, context)

        # drop m2m relation tables
        for table in to_drop_table:
            cr.execute('DROP TABLE %s CASCADE'% table,)
            _logger.info('Dropped table %s', table)

class ir_model_access(osv.osv):
    _name = 'ir.model.access'
    _columns = {
        'name': fields.char('Name', required=True, select=True),
        'active': fields.boolean('Active', help='If you uncheck the active field, it will disable the ACL without deleting it (if you delete a native ACL, it will be re-created when you reload the module.'),
        'model_id': fields.many2one('ir.model', 'Object', required=True, domain=[('transient','=', False)], select=True, ondelete='cascade'),
        'group_id': fields.many2one('res.groups', 'Group', ondelete='cascade', select=True),
        'perm_read': fields.boolean('Read Access'),
        'perm_write': fields.boolean('Write Access'),
        'perm_create': fields.boolean('Create Access'),
        'perm_unlink': fields.boolean('Delete Access'),
    }
    _defaults = {
        'active': True,
    }

    def check_groups(self, cr, uid, group):
        grouparr  = group.split('.')
        if not grouparr:
            return False
        cr.execute("select 1 from res_groups_users_rel where uid=%s and gid IN (select res_id from ir_model_data where module=%s and name=%s)", (uid, grouparr[0], grouparr[1],))
        return bool(cr.fetchone())

    def check_group(self, cr, uid, model, mode, group_ids):
        """ Check if a specific group has the access mode to the specified model"""
        assert mode in ['read','write','create','unlink'], 'Invalid access mode'

        if isinstance(model, BaseModel):
            assert model._name == 'ir.model', 'Invalid model object'
            model_name = model.name
        else:
            model_name = model

        if isinstance(group_ids, (int, long)):
            group_ids = [group_ids]
        for group_id in group_ids:
            cr.execute("SELECT perm_" + mode + " "
                   "  FROM ir_model_access a "
                   "  JOIN ir_model m ON (m.id = a.model_id) "
                   " WHERE m.model = %s AND a.active IS True "
                   " AND a.group_id = %s", (model_name, group_id)
                   )
            r = cr.fetchone()
            if r is None:
                cr.execute("SELECT perm_" + mode + " "
                       "  FROM ir_model_access a "
                       "  JOIN ir_model m ON (m.id = a.model_id) "
                       " WHERE m.model = %s AND a.active IS True "
                       " AND a.group_id IS NULL", (model_name, )
                       )
                r = cr.fetchone()

            access = bool(r and r[0])
            if access:
                return True
        # pass no groups -> no access
        return False

    def group_names_with_access(self, cr, model_name, access_mode):
        """Returns the names of visible groups which have been granted ``access_mode`` on
           the model ``model_name``.
           :rtype: list
        """
        assert access_mode in ['read','write','create','unlink'], 'Invalid access mode: %s' % access_mode
        cr.execute('''SELECT
                        c.name, g.name
                      FROM
                        ir_model_access a
                        JOIN ir_model m ON (a.model_id=m.id)
                        JOIN res_groups g ON (a.group_id=g.id)
                        LEFT JOIN ir_module_category c ON (c.id=g.category_id)
                      WHERE
                        m.model=%s AND
                        a.active IS True AND
                        a.perm_''' + access_mode, (model_name,))
        return [('%s/%s' % x) if x[0] else x[1] for x in cr.fetchall()]

    # The context parameter is useful when the method translates error messages.
    # But as the method raises an exception in that case,  the key 'lang' might
    # not be really necessary as a cache key, unless the `ormcache_context`
    # decorator catches the exception (it does not at the moment.)
    @tools.ormcache_context('uid', 'model', 'mode', 'raise_exception', keys=('lang',))
    def check(self, cr, uid, model, mode='read', raise_exception=True, context=None):
        if uid==1:
            # User root have all accesses
            # TODO: exclude xml-rpc requests
            return True

        assert mode in ['read','write','create','unlink'], 'Invalid access mode'

        if isinstance(model, BaseModel):
            assert model._name == 'ir.model', 'Invalid model object'
            model_name = model.model
        else:
            model_name = model

        # TransientModel records have no access rights, only an implicit access rule
        if model_name not in self.pool:
            _logger.error('Missing model %s' % (model_name, ))
        elif self.pool[model_name].is_transient():
            return True

        # We check if a specific rule exists
        cr.execute('SELECT MAX(CASE WHEN perm_' + mode + ' THEN 1 ELSE 0 END) '
                   '  FROM ir_model_access a '
                   '  JOIN ir_model m ON (m.id = a.model_id) '
                   '  JOIN res_groups_users_rel gu ON (gu.gid = a.group_id) '
                   ' WHERE m.model = %s '
                   '   AND gu.uid = %s '
                   '   AND a.active IS True '
                   , (model_name, uid,)
                   )
        r = cr.fetchone()[0]

        if r is None:
            # there is no specific rule. We check the generic rule
            cr.execute('SELECT MAX(CASE WHEN perm_' + mode + ' THEN 1 ELSE 0 END) '
                       '  FROM ir_model_access a '
                       '  JOIN ir_model m ON (m.id = a.model_id) '
                       ' WHERE a.group_id IS NULL '
                       '   AND m.model = %s '
                       '   AND a.active IS True '
                       , (model_name,)
                       )
            r = cr.fetchone()[0]

        if not r and raise_exception:
            groups = '\n\t'.join('- %s' % g for g in self.group_names_with_access(cr, model_name, mode))
            msg_heads = {
                # Messages are declared in extenso so they are properly exported in translation terms
                'read': _("Sorry, you are not allowed to access this document."),
                'write':  _("Sorry, you are not allowed to modify this document."),
                'create': _("Sorry, you are not allowed to create this kind of document."),
                'unlink': _("Sorry, you are not allowed to delete this document."),
            }
            if groups:
                msg_tail = _("Only users with the following access level are currently allowed to do that") + ":\n%s\n\n(" + _("Document model") + ": %s)"
                msg_params = (groups, model_name)
            else:
                msg_tail = _("Please contact your system administrator if you think this is an error.") + "\n\n(" + _("Document model") + ": %s)"
                msg_params = (model_name,)
            _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s', mode, uid, model_name)
            msg = '%s %s' % (msg_heads[mode], msg_tail)
            raise openerp.exceptions.AccessError(msg % msg_params)
        return bool(r)

    __cache_clearing_methods = []

    def register_cache_clearing_method(self, model, method):
        self.__cache_clearing_methods.append((model, method))

    def unregister_cache_clearing_method(self, model, method):
        try:
            i = self.__cache_clearing_methods.index((model, method))
            del self.__cache_clearing_methods[i]
        except ValueError:
            pass

    def call_cache_clearing_methods(self, cr):
        self.invalidate_cache(cr, SUPERUSER_ID)
        self.check.clear_cache(self)    # clear the cache of check function
        for model, method in self.__cache_clearing_methods:
            if model in self.pool:
                getattr(self.pool[model], method)()

    #
    # Check rights on actions
    #
    def write(self, cr, uid, ids, values, context=None):
        self.call_cache_clearing_methods(cr)
        res = super(ir_model_access, self).write(cr, uid, ids, values, context=context)
        return res

    def create(self, cr, uid, values, context=None):
        self.call_cache_clearing_methods(cr)
        res = super(ir_model_access, self).create(cr, uid, values, context=context)
        return res

    def unlink(self, cr, uid, ids, context=None):
        self.call_cache_clearing_methods(cr)
        res = super(ir_model_access, self).unlink(cr, uid, ids, context=context)
        return res

class ir_model_data(osv.osv):
    """Holds external identifier keys for records in the database.
       This has two main uses:

           * allows easy data integration with third-party systems,
             making import/export/sync of data possible, as records
             can be uniquely identified across multiple systems
           * allows tracking the origin of data installed by OpenERP
             modules themselves, thus making it possible to later
             update them seamlessly.
    """
    _name = 'ir.model.data'
    _order = 'module,model,name'

    def name_get(self, cr, uid, ids, context=None):
        bymodel = defaultdict(dict)
        names = {}

        for res in self.browse(cr, uid, ids, context=context):
            bymodel[res.model][res.res_id] = res
            names[res.id] = res.complete_name
            #result[res.model][res.res_id] = res.id

        for model, id_map in bymodel.iteritems():
            try:
                ng = dict(self.pool[model].name_get(cr, uid, id_map.keys(), context=context))
            except Exception:
                pass
            else:
                for r in id_map.itervalues():
                    names[r.id] = ng.get(r.res_id, r.complete_name)

        return [(i, names[i]) for i in ids]

    def _complete_name_get(self, cr, uid, ids, prop, unknow_none, context=None):
        result = {}
        for res in self.browse(cr, uid, ids, context=context):
            result[res.id] = (res.module and (res.module + '.') or '')+res.name
        return result

    _columns = {
        'name': fields.char('External Identifier', required=True,
                            help="External Key/Identifier that can be used for "
                                 "data integration with third-party systems"),
        'complete_name': fields.function(_complete_name_get, type='char', string='Complete ID'),
        'model': fields.char('Model Name', required=True),
        'module': fields.char('Module', required=True),
        'res_id': fields.integer('Record ID', help="ID of the target record in the database"),
        'noupdate': fields.boolean('Non Updatable'),
        'date_update': fields.datetime('Update Date'),
        'date_init': fields.datetime('Init Date')
    }
    _defaults = {
        'date_init': fields.datetime.now,
        'date_update': fields.datetime.now,
        'noupdate': False,
        'module': ''
    }

    def __init__(self, pool, cr):
        osv.osv.__init__(self, pool, cr)
        # also stored in pool to avoid being discarded along with this osv instance
        if getattr(pool, 'model_data_reference_ids', None) is None:
            self.pool.model_data_reference_ids = {}
        # put loads on the class, in order to share it among all instances
        type(self).loads = self.pool.model_data_reference_ids

    def _auto_init(self, cr, context=None):
        res = super(ir_model_data, self)._auto_init(cr, context)
        cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'ir_model_data_module_name_uniq_index'")
        if not cr.fetchone():
            cr.execute('CREATE UNIQUE INDEX ir_model_data_module_name_uniq_index ON ir_model_data (module, name)')
        cr.execute("SELECT indexname FROM pg_indexes WHERE indexname = 'ir_model_data_model_res_id_index'")
        if not cr.fetchone():
            cr.execute('CREATE INDEX ir_model_data_model_res_id_index ON ir_model_data (model, res_id)')
        return res

    # NEW V8 API
    @tools.ormcache('xmlid')
    def xmlid_lookup(self, cr, uid, xmlid):
        """Low level xmlid lookup
        Return (id, res_model, res_id) or raise ValueError if not found
        """
        module, name = xmlid.split('.', 1)
        ids = self.search(cr, uid, [('module','=',module), ('name','=', name)])
        if not ids:
            raise ValueError('External ID not found in the system: %s' % (xmlid))
        # the sql constraints ensure us we have only one result
        res = self.read(cr, uid, ids[0], ['model', 'res_id'])
        if not res['res_id']:
            raise ValueError('External ID not found in the system: %s' % (xmlid))
        return ids[0], res['model'], res['res_id']
    
    def xmlid_to_res_model_res_id(self, cr, uid, xmlid, raise_if_not_found=False):
        """ Return (res_model, res_id)"""
        try:
            return self.xmlid_lookup(cr, uid, xmlid)[1:3]
        except ValueError:
            if raise_if_not_found:
                raise
            return (False, False)

    def xmlid_to_res_id(self, cr, uid, xmlid, raise_if_not_found=False):
        """ Returns res_id """
        return self.xmlid_to_res_model_res_id(cr, uid, xmlid, raise_if_not_found)[1]

    def xmlid_to_object(self, cr, uid, xmlid, raise_if_not_found=False, context=None):
        """ Return a browse_record
        if not found and raise_if_not_found is False return None
        """ 
        t = self.xmlid_to_res_model_res_id(cr, uid, xmlid, raise_if_not_found)
        res_model, res_id = t

        if res_model and res_id:
            record = self.pool[res_model].browse(cr, uid, res_id, context=context)
            if record.exists():
                return record
            if raise_if_not_found:
                raise ValueError('No record found for unique ID %s. It may have been deleted.' % (xmlid))
        return None

    # OLD API
    def _get_id(self, cr, uid, module, xml_id):
        """Returns the id of the ir.model.data record corresponding to a given module and xml_id (cached) or raise a ValueError if not found"""
        return self.xmlid_lookup(cr, uid, "%s.%s" % (module, xml_id))[0]

    def get_object_reference(self, cr, uid, module, xml_id):
        """Returns (model, res_id) corresponding to a given module and xml_id (cached) or raise ValueError if not found"""
        return self.xmlid_lookup(cr, uid, "%s.%s" % (module, xml_id))[1:3]

    def check_object_reference(self, cr, uid, module, xml_id, raise_on_access_error=False):
        """Returns (model, res_id) corresponding to a given module and xml_id (cached), if and only if the user has the necessary access rights
        to see that object, otherwise raise a ValueError if raise_on_access_error is True or returns a tuple (model found, False)"""
        model, res_id = self.get_object_reference(cr, uid, module, xml_id)
        #search on id found in result to check if current user has read access right
        check_right = self.pool.get(model).search(cr, uid, [('id', '=', res_id)])
        if check_right:
            return model, res_id
        if raise_on_access_error:
            raise AccessError('Not enough access rights on the external ID: %s.%s' % (module, xml_id))
        return model, False

    def get_object(self, cr, uid, module, xml_id, context=None):
        """ Returns a browsable record for the given module name and xml_id.
            If not found, raise a ValueError or return None, depending
            on the value of `raise_exception`.
        """
        return self.xmlid_to_object(cr, uid, "%s.%s" % (module, xml_id), raise_if_not_found=True, context=context)

    def _update_dummy(self,cr, uid, model, module, xml_id=False, store=True):
        if not xml_id:
            return False
        id = False
        try:
            # One step to check the ID is defined and the record actually exists
            record = self.get_object(cr, uid, module, xml_id)
            if record:
                id = record.id
                self.loads[(module,xml_id)] = (model,id)
                for table, inherit_field in self.pool[model]._inherits.iteritems():
                    parent_id = record[inherit_field].id
                    parent_xid = '%s_%s' % (xml_id, table.replace('.', '_'))
                    self.loads[(module, parent_xid)] = (table, parent_id)
        except Exception:
            pass
        return id

    def clear_caches(self):
        """ Clears all orm caches on the object's methods

        :returns: itself
        """
        self.xmlid_lookup.clear_cache(self)
        return self

    def unlink(self, cr, uid, ids, context=None):
        """ Regular unlink method, but make sure to clear the caches. """
        self.clear_caches()
        return super(ir_model_data,self).unlink(cr, uid, ids, context=context)

    def _update(self,cr, uid, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False, context=None):
        model_obj = self.pool[model]
        if not context:
            context = {}
        # records created during module install should not display the messages of OpenChatter
        context = dict(context, install_mode=True)
        if xml_id and ('.' in xml_id):
            assert len(xml_id.split('.'))==2, _("'%s' contains too many dots. XML ids should not contain dots ! These are used to refer to other modules data, as in module.reference_id") % xml_id
            module, xml_id = xml_id.split('.')
        action_id = False
        if xml_id:
            cr.execute('''SELECT imd.id, imd.res_id, md.id, imd.model, imd.noupdate
                          FROM ir_model_data imd LEFT JOIN %s md ON (imd.res_id = md.id)
                          WHERE imd.module=%%s AND imd.name=%%s''' % model_obj._table,
                          (module, xml_id))
            results = cr.fetchall()
            for imd_id2,res_id2,real_id2,real_model,noupdate_imd in results:
                # In update mode, do not update a record if it's ir.model.data is flagged as noupdate
                if mode == 'update' and noupdate_imd:
                    return res_id2
                if not real_id2:
                    self.clear_caches()
                    cr.execute('delete from ir_model_data where id=%s', (imd_id2,))
                    res_id = False
                else:
                    assert model == real_model, "External ID conflict, %s already refers to a `%s` record,"\
                        " you can't define a `%s` record with this ID." % (xml_id, real_model, model)
                    res_id,action_id = res_id2,imd_id2

        if action_id and res_id:
            model_obj.write(cr, uid, [res_id], values, context=context)
            self.write(cr, SUPERUSER_ID, [action_id], {
                'date_update': time.strftime('%Y-%m-%d %H:%M:%S'),
                },context=context)
        elif res_id:
            model_obj.write(cr, uid, [res_id], values, context=context)
            if xml_id:
                if model_obj._inherits:
                    for table in model_obj._inherits:
                        inherit_id = model_obj.browse(cr, uid,
                                res_id,context=context)[model_obj._inherits[table]]
                        self.create(cr, SUPERUSER_ID, {
                            'name': xml_id + '_' + table.replace('.', '_'),
                            'model': table,
                            'module': module,
                            'res_id': inherit_id.id,
                            'noupdate': noupdate,
                            },context=context)
                self.create(cr, SUPERUSER_ID, {
                    'name': xml_id,
                    'model': model,
                    'module':module,
                    'res_id':res_id,
                    'noupdate': noupdate,
                    },context=context)
        else:
            if mode=='init' or (mode=='update' and xml_id):
                inherit_xml_ids = []
                if xml_id:
                    for table, field_name in model_obj._inherits.items():
                        xml_ids = self.pool['ir.model.data'].search(cr, uid, [
                            ('module', '=', module),
                            ('name', '=', xml_id + '_' + table.replace('.', '_')),
                        ], context=context)
                        # XML ID found in the database, try to recover an existing record
                        if xml_ids:
                            found_xml_id = self.pool['ir.model.data'].browse(cr, uid, xml_ids[0], context=context)
                            record = self.pool[found_xml_id.model].browse(cr, uid, [found_xml_id.res_id], context=context)[0]
                            # The record exists, store the id and don't recreate the XML ID
                            if record.exists():
                                inherit_xml_ids.append(found_xml_id.model)
                                values[field_name] = found_xml_id.res_id
                            # Orphan XML ID, delete it
                            else:
                                found_xml_id.unlink()

                res_id = model_obj.create(cr, uid, values, context=context)
                if xml_id:
                    if model_obj._inherits:
                        for table in model_obj._inherits:
                            if table in inherit_xml_ids:
                                continue

                            inherit_id = model_obj.browse(cr, uid,
                                    res_id,context=context)[model_obj._inherits[table]]
                            self.create(cr, SUPERUSER_ID, {
                                'name': xml_id + '_' + table.replace('.', '_'),
                                'model': table,
                                'module': module,
                                'res_id': inherit_id.id,
                                'noupdate': noupdate,
                                },context=context)
                    self.create(cr, SUPERUSER_ID, {
                        'name': xml_id,
                        'model': model,
                        'module': module,
                        'res_id': res_id,
                        'noupdate': noupdate
                        },context=context)
        if xml_id and res_id:
            self.loads[(module, xml_id)] = (model, res_id)
            for table, inherit_field in model_obj._inherits.iteritems():
                inherit_id = model_obj.read(cr, uid, [res_id],
                        [inherit_field])[0][inherit_field]
                self.loads[(module, xml_id + '_' + table.replace('.', '_'))] = (table, inherit_id)
        return res_id

    def ir_set(self, cr, uid, key, key2, name, models, value, replace=True, isobject=False, meta=None, xml_id=False):
        ir_values_obj = openerp.registry(cr.dbname)['ir.values']
        ir_values_obj.set(cr, uid, key, key2, name, models, value, replace, isobject, meta)
        return True

    def _module_data_uninstall(self, cr, uid, modules_to_remove, context=None):
        """Deletes all the records referenced by the ir.model.data entries
        ``ids`` along with their corresponding database backed (including
        dropping tables, columns, FKs, etc, as long as there is no other
        ir.model.data entry holding a reference to them (which indicates that
        they are still owned by another module). 
        Attempts to perform the deletion in an appropriate order to maximize
        the chance of gracefully deleting all records.
        This step is performed as part of the full uninstallation of a module.
        """ 

        ids = self.search(cr, uid, [('module', 'in', modules_to_remove)])

        if uid != 1 and not self.pool['ir.model.access'].check_groups(cr, uid, "base.group_system"):
            raise AccessError(_('Administrator access is required to uninstall a module'))

        context = dict(context or {})
        context[MODULE_UNINSTALL_FLAG] = True # enable model/field deletion

        ids_set = set(ids)
        wkf_todo = []
        to_unlink = []
        ids.sort()
        ids.reverse()
        for data in self.browse(cr, uid, ids, context):
            model = data.model
            res_id = data.res_id

            pair_to_unlink = (model, res_id)
            if pair_to_unlink not in to_unlink:
                to_unlink.append(pair_to_unlink)

            if model == 'workflow.activity':
                # Special treatment for workflow activities: temporarily revert their
                # incoming transition and trigger an update to force all workflow items
                # to move out before deleting them
                cr.execute('select res_type,res_id from wkf_instance where id IN (select inst_id from wkf_workitem where act_id=%s)', (res_id,))
                wkf_todo.extend(cr.fetchall())
                cr.execute("update wkf_transition set condition='True', group_id=NULL, signal=NULL,act_to=act_from,act_from=%s where act_to=%s", (res_id,res_id))
                self.invalidate_cache(cr, uid, context=context)

        for model,res_id in wkf_todo:
            try:
                openerp.workflow.trg_write(uid, model, res_id, cr)
            except Exception:
                _logger.info('Unable to force processing of workflow for item %s@%s in order to leave activity to be deleted', res_id, model, exc_info=True)

        def unlink_if_refcount(to_unlink):
            for model, res_id in to_unlink:
                external_ids = self.search(cr, uid, [('model', '=', model),('res_id', '=', res_id)])
                if set(external_ids)-ids_set:
                    # if other modules have defined this record, we must not delete it
                    continue
                if model == 'ir.model.fields':
                    # Don't remove the LOG_ACCESS_COLUMNS unless _log_access
                    # has been turned off on the model.
                    field = self.pool[model].browse(cr, uid, [res_id], context=context)[0]
                    if not field.exists():
                        _logger.info('Deleting orphan external_ids %s', external_ids)
                        self.unlink(cr, uid, external_ids)
                        continue
                    if field.name in openerp.models.LOG_ACCESS_COLUMNS and field.model in self.pool and self.pool[field.model]._log_access:
                        continue
                    if field.name == 'id':
                        continue
                _logger.info('Deleting %s@%s', res_id, model)
                try:
                    cr.execute('SAVEPOINT record_unlink_save')
                    self.pool[model].unlink(cr, uid, [res_id], context=context)
                except Exception:
                    _logger.info('Unable to delete %s@%s', res_id, model, exc_info=True)
                    cr.execute('ROLLBACK TO SAVEPOINT record_unlink_save')
                else:
                    cr.execute('RELEASE SAVEPOINT record_unlink_save')

        # Remove non-model records first, then model fields, and finish with models
        unlink_if_refcount((model, res_id) for model, res_id in to_unlink
                                if model not in ('ir.model','ir.model.fields','ir.model.constraint'))
        unlink_if_refcount((model, res_id) for model, res_id in to_unlink
                                if model == 'ir.model.constraint')

        ir_module_module = self.pool['ir.module.module']
        ir_model_constraint = self.pool['ir.model.constraint']
        modules_to_remove_ids = ir_module_module.search(cr, uid, [('name', 'in', modules_to_remove)], context=context)
        constraint_ids = ir_model_constraint.search(cr, uid, [('module', 'in', modules_to_remove_ids)], context=context)
        ir_model_constraint._module_data_uninstall(cr, uid, constraint_ids, context)

        unlink_if_refcount((model, res_id) for model, res_id in to_unlink
                                if model == 'ir.model.fields')

        ir_model_relation = self.pool['ir.model.relation']
        relation_ids = ir_model_relation.search(cr, uid, [('module', 'in', modules_to_remove_ids)])
        ir_model_relation._module_data_uninstall(cr, uid, relation_ids, context)

        unlink_if_refcount((model, res_id) for model, res_id in to_unlink
                                if model == 'ir.model')


        self.unlink(cr, uid, ids, context)

    def _process_end(self, cr, uid, modules):
        """ Clear records removed from updated module data.
        This method is called at the end of the module loading process.
        It is meant to removed records that are no longer present in the
        updated data. Such records are recognised as the one with an xml id
        and a module in ir_model_data and noupdate set to false, but not
        present in self.loads.
        """
        if not modules or config.get('import_partial'):
            return True

        bad_imd_ids = []
        context = {MODULE_UNINSTALL_FLAG: True}
        cr.execute("""SELECT id,name,model,res_id,module FROM ir_model_data
                      WHERE module IN %s AND res_id IS NOT NULL AND noupdate=%s ORDER BY id DESC
                   """, (tuple(modules), False))
        for (id, name, model, res_id, module) in cr.fetchall():
            if (module, name) not in self.loads:
                if model in self.pool:
                    _logger.info('Deleting %s@%s (%s.%s)', res_id, model, module, name)
                    if self.pool[model].exists(cr, uid, [res_id], context=context):
                        self.pool[model].unlink(cr, uid, [res_id], context=context)
                    else:
                        bad_imd_ids.append(id)
        if bad_imd_ids:
            self.unlink(cr, uid, bad_imd_ids, context=context)
        self.loads.clear()

class wizard_model_menu(osv.osv_memory):
    _name = 'wizard.ir.model.menu.create'
    _columns = {
        'menu_id': fields.many2one('ir.ui.menu', 'Parent Menu', required=True),
        'name': fields.char('Menu Name', required=True),
    }

    def menu_create(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        model_pool = self.pool.get('ir.model')
        for menu in self.browse(cr, uid, ids, context):
            model = model_pool.browse(cr, uid, context.get('model_id'), context=context)
            val = {
                'name': menu.name,
                'res_model': model.model,
                'view_type': 'form',
                'view_mode': 'tree,form'
            }
            action_id = self.pool.get('ir.actions.act_window').create(cr, uid, val)
            self.pool.get('ir.ui.menu').create(cr, uid, {
                'name': menu.name,
                'parent_id': menu.menu_id.id,
                'action': 'ir.actions.act_window,%d' % (action_id,)
            }, context)
        return {'type':'ir.actions.act_window_close'}
