# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import datetime
import dateutil
import logging
import time
from collections import defaultdict

from odoo import api, fields, models, SUPERUSER_ID, tools,  _
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.modules.registry import Registry
from odoo.osv import expression
from odoo.tools import pycompat
from odoo.tools.safe_eval import safe_eval

_logger = logging.getLogger(__name__)

MODULE_UNINSTALL_FLAG = '_force_unlink'


# base environment for doing a safe_eval
SAFE_EVAL_BASE = {
    'datetime': datetime,
    'dateutil': dateutil,
    'time': time,
}

def make_compute(text, deps):
    """ Return a compute function from its code body and dependencies. """
    func = lambda self: safe_eval(text, SAFE_EVAL_BASE, {'self': self}, mode="exec")
    deps = [arg.strip() for arg in (deps or "").split(",")]
    return api.depends(*deps)(func)


# generic INSERT and UPDATE queries
INSERT_QUERY = "INSERT INTO {table} ({cols}) VALUES ({vals}) RETURNING id"
UPDATE_QUERY = "UPDATE {table} SET {assignment} WHERE {condition} RETURNING id"

def query_insert(cr, table, values):
    query = INSERT_QUERY.format(
        table=table,
        cols=",".join(values),
        vals=",".join("%({0})s".format(v) for v in values),
    )
    cr.execute(query, values)

def query_update(cr, table, values, selectors):
    setters = set(values) - set(selectors)
    query = UPDATE_QUERY.format(
        table=table,
        assignment=",".join("{0}=%({0})s".format(s) for s in setters),
        condition=" AND ".join("{0}=%({0})s".format(s) for s in selectors),
    )
    cr.execute(query, values)


#
# IMPORTANT: this must be the first model declared in the module
#
class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _name = 'base'


class Unknown(models.AbstractModel):
    """
    Abstract model used as a substitute for relational fields with an unknown
    comodel.
    """
    _name = '_unknown'


class IrModel(models.Model):
    _name = 'ir.model'
    _description = "Models"
    _order = 'model'

    def _default_field_id(self):
        if self.env.context.get('install_mode'):
            return []                   # no default field when importing
        return [(0, 0, {'name': 'x_name', 'field_description': 'Name', 'ttype': 'char'})]

    name = fields.Char(string='Model Description', translate=True, required=True)
    model = fields.Char(default='x_', required=True, index=True)
    info = fields.Text(string='Information')
    field_id = fields.One2many('ir.model.fields', 'model_id', string='Fields', required=True, copy=True,
                               default=_default_field_id)
    inherited_model_ids = fields.Many2many('ir.model', compute='_inherited_models', string="Inherited models",
                                           help="The list of models that extends the current model.")
    state = fields.Selection([('manual', 'Custom Object'), ('base', 'Base Object')], string='Type', default='manual', readonly=True)
    access_ids = fields.One2many('ir.model.access', 'model_id', string='Access')
    transient = fields.Boolean(string="Transient Model")
    modules = fields.Char(compute='_in_modules', string='In Apps', help='List of modules in which the object is defined or inherited')
    view_ids = fields.One2many('ir.ui.view', compute='_view_ids', string='Views')
    count = fields.Integer(compute='_compute_count', string="Count (incl. archived)",
                           help="Total number of records in this model")

    @api.depends()
    def _inherited_models(self):
        for model in self:
            parent_names = list(self.env[model.model]._inherits)
            if parent_names:
                model.inherited_model_ids = self.search([('model', 'in', parent_names)])

    @api.depends()
    def _in_modules(self):
        installed_modules = self.env['ir.module.module'].search([('state', '=', 'installed')])
        installed_names = set(installed_modules.mapped('name'))
        xml_ids = models.Model._get_external_ids(self)
        for model in self:
            module_names = set(xml_id.split('.')[0] for xml_id in xml_ids[model.id])
            model.modules = ", ".join(sorted(installed_names & module_names))

    @api.depends()
    def _view_ids(self):
        for model in self:
            model.view_ids = self.env['ir.ui.view'].search([('model', '=', model.model)])

    @api.depends()
    def _compute_count(self):
        cr = self.env.cr
        for model in self:
            records = self.env[model.model]
            if not records._abstract:
                cr.execute('SELECT COUNT(*) FROM "%s"' % records._table)
                model.count = cr.fetchone()[0]

    @api.constrains('model')
    def _check_model_name(self):
        for model in self:
            if model.state == 'manual':
                if not model.model.startswith('x_'):
                    raise ValidationError(_("The model name must start with 'x_'."))
            if not models.check_object_name(model.model):
                raise ValidationError(_("The model name can only contain lowercase characters, digits, underscores and dots."))

    _sql_constraints = [
        ('obj_name_uniq', 'unique (model)', 'Each model must be unique!'),
    ]

    def _get(self, name):
        """ Return the (sudoed) `ir.model` record with the given name.
        The result may be an empty recordset if the model is not found.
        """
        model_id = self._get_id(name) if name else False
        return self.sudo().browse(model_id)

    @tools.ormcache('name')
    def _get_id(self, name):
        self.env.cr.execute("SELECT id FROM ir_model WHERE model=%s", (name,))
        result = self.env.cr.fetchone()
        return result and result[0]

    # overridden to allow searching both on model name (field 'model') and model
    # description (field 'name')
    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100):
        if args is None:
            args = []
        domain = args + ['|', ('model', operator, name), ('name', operator, name)]
        return super(IrModel, self).search(domain, limit=limit).name_get()

    def _drop_table(self):
        for model in self:
            table = self.env[model.model]._table
            kind = tools.table_kind(self._cr, table)
            if kind == 'v':
                self._cr.execute('DROP VIEW "%s"' % table)
            elif kind == 'r':
                self._cr.execute('DROP TABLE "%s" CASCADE' % table)
        return True

    @api.multi
    def unlink(self):
        # Prevent manual deletion of module tables
        if not self._context.get(MODULE_UNINSTALL_FLAG):
            for model in self:
                if model.state != 'manual':
                    raise UserError(_("Model '%s' contains module data and cannot be removed!") % model.name)
                # prevent screwing up fields that depend on these models' fields
                model.field_id._prepare_update()

        self._drop_table()
        res = super(IrModel, self).unlink()

        # Reload registry for normal unlink only. For module uninstall, the
        # reload is done independently in odoo.modules.loading.
        if not self._context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this automatically removes model from registry
            self.pool.setup_models(self._cr)

        return res

    @api.multi
    def write(self, vals):
        if '__last_update' in self._context:
            self = self.with_context({k: v for k, v in self._context.items() if k != '__last_update'})
        if 'model' in vals and any(rec.model != vals['model'] for rec in self):
            raise UserError(_('Field "Model" cannot be modified on models.'))
        if 'state' in vals and any(rec.state != vals['state'] for rec in self):
            raise UserError(_('Field "Type" cannot be modified on models.'))
        if 'transient' in vals and any(rec.transient != vals['transient'] for rec in self):
            raise UserError(_('Field "Transient Model" cannot be modified on models.'))
        # Filter out operations 4 from field id, because the web client always
        # writes (4,id,False) even for non dirty items.
        if 'field_id' in vals:
            vals['field_id'] = [op for op in vals['field_id'] if op[0] != 4]
        return super(IrModel, self).write(vals)

    @api.model
    def create(self, vals):
        res = super(IrModel, self).create(vals)
        if vals.get('state', 'manual') == 'manual':
            # setup models; this automatically adds model in registry
            self.pool.setup_models(self._cr)
            # update database schema
            self.pool.init_models(self._cr, [vals['model']], dict(self._context, update_custom_fields=True))
        return res

    @api.model
    def name_create(self, name):
        """ Infer the model from the name. E.g.: 'My New Model' should become 'x_my_new_model'. """
        vals = {
            'name': name,
            'model': 'x_' + '_'.join(name.lower().split(' ')),
        }
        return self.create(vals).name_get()[0]

    def _reflect_model_params(self, model):
        """ Return the values to write to the database for the given model. """
        return {
            'model': model._name,
            'name': model._description,
            'info': next(cls.__doc__ for cls in type(model).mro() if cls.__doc__),
            'state': 'manual' if model._custom else 'base',
            'transient': model._transient,
        }

    def _reflect_model(self, model):
        """ Reflect the given model and return the corresponding record. Also
            create entries in 'ir.model.data'.
        """
        cr = self.env.cr

        # create/update the entries in 'ir.model' and 'ir.model.data'
        params = self._reflect_model_params(model)
        query_update(cr, self._table, params, ['model'])
        if not cr.rowcount:
            query_insert(cr, self._table, params)

        record = self.browse(cr.fetchone())
        self.pool.post_init(record.modified, set(params) - {'model', 'state'})

        if model._module == self._context.get('module'):
            # self._module is the name of the module that last extended self
            xmlid = 'model_' + model._name.replace('.', '_')
            cr.execute("SELECT * FROM ir_model_data WHERE name=%s AND module=%s",
                       (xmlid, self._context['module']))
            if not cr.rowcount:
                cr.execute(""" INSERT INTO ir_model_data (module, name, model, res_id, date_init, date_update)
                               VALUES (%s, %s, %s, %s, (now() at time zone 'UTC'), (now() at time zone 'UTC')) """,
                           (self._context['module'], xmlid, record._name, record.id))

        return record

    @api.model
    def _instanciate(self, model_data):
        """ Return a class for the custom model given by parameters ``model_data``. """
        class CustomModel(models.Model):
            _name = pycompat.to_native(model_data['model'])
            _description = model_data['name']
            _module = False
            _custom = True
            _transient = bool(model_data['transient'])
            __doc__ = model_data['info']

        return CustomModel

    def _add_manual_models(self):
        """ Add extra models to the registry. """
        # clean up registry first
        custom_models = [name for name, model_class in self.pool.items() if model_class._custom]
        for name in custom_models:
            del self.pool.models[name]
        # add manual models
        cr = self.env.cr
        cr.execute('SELECT * FROM ir_model WHERE state=%s', ['manual'])
        for model_data in cr.dictfetchall():
            model_class = self._instanciate(model_data)
            model_class._build_model(self.pool, cr)


# retrieve field types defined by the framework only (not extensions)
FIELD_TYPES = [(key, key) for key in sorted(fields.Field.by_type)]


class IrModelFields(models.Model):
    _name = 'ir.model.fields'
    _description = "Fields"
    _order = "name"
    _rec_name = 'field_description'

    name = fields.Char(string='Field Name', default='x_', required=True, index=True)
    complete_name = fields.Char(index=True)
    model = fields.Char(string='Object Name', required=True, index=True,
                        help="The technical name of the model this field belongs to")
    relation = fields.Char(string='Object Relation',
                           help="For relationship fields, the technical name of the target model")
    relation_field = fields.Char(help="For one2many fields, the field on the target model that implement the opposite many2one relationship")
    model_id = fields.Many2one('ir.model', string='Model', required=True, index=True, ondelete='cascade',
                               help="The model this field belongs to")
    field_description = fields.Char(string='Field Label', default='', required=True, translate=True)
    help = fields.Text(string='Field Help', translate=True)
    ttype = fields.Selection(selection=FIELD_TYPES, string='Field Type', required=True)
    selection = fields.Char(string='Selection Options', default="",
                            help="List of options for a selection field, "
                                 "specified as a Python expression defining a list of (key, label) pairs. "
                                 "For example: [('blue','Blue'),('yellow','Yellow')]")
    copy = fields.Boolean(string='Copied', help="Whether the value is copied when duplicating a record.")
    related = fields.Char(string='Related Field', help="The corresponding related field, if any. This must be a dot-separated list of field names.")
    required = fields.Boolean()
    readonly = fields.Boolean()
    index = fields.Boolean(string='Indexed')
    translate = fields.Boolean(string='Translatable', help="Whether values for this field can be translated (enables the translation mechanism for that field)")
    size = fields.Integer()
    state = fields.Selection([('manual', 'Custom Field'), ('base', 'Base Field')], string='Type', default='manual', required=True, readonly=True, index=True)
    on_delete = fields.Selection([('cascade', 'Cascade'), ('set null', 'Set NULL'), ('restrict', 'Restrict')],
                                 string='On Delete', default='set null', help='On delete property for many2one fields')
    domain = fields.Char(default="[]", help="The optional domain to restrict possible values for relationship fields, "
                                            "specified as a Python expression defining a list of triplets. "
                                            "For example: [('color','=','red')]")
    groups = fields.Many2many('res.groups', 'ir_model_fields_group_rel', 'field_id', 'group_id')
    selectable = fields.Boolean(default=True)
    modules = fields.Char(compute='_in_modules', string='In Apps', help='List of modules in which the field is defined')
    relation_table = fields.Char(help="Used for custom many2many fields to define a custom relation table name")
    column1 = fields.Char(string='Column 1', help="Column referring to the record in the model table")
    column2 = fields.Char(string="Column 2", help="Column referring to the record in the comodel table")
    compute = fields.Text(help="Code to compute the value of the field.\n"
                               "Iterate on the recordset 'self' and assign the field's value:\n\n"
                               "    for record in self:\n"
                               "        record['size'] = len(record.name)\n\n"
                               "Modules time, datetime, dateutil are available.")
    depends = fields.Char(string='Dependencies', help="Dependencies of compute method; "
                                                      "a list of comma-separated field names, like\n\n"
                                                      "    name, partner_id.name")
    store = fields.Boolean(string='Stored', default=True, help="Whether the value is stored in the database.")

    @api.depends()
    def _in_modules(self):
        installed_modules = self.env['ir.module.module'].search([('state', '=', 'installed')])
        installed_names = set(installed_modules.mapped('name'))
        xml_ids = models.Model._get_external_ids(self)
        for field in self:
            module_names = set(xml_id.split('.')[0] for xml_id in xml_ids[field.id])
            field.modules = ", ".join(sorted(installed_names & module_names))

    @api.model
    def _check_selection(self, selection):
        try:
            items = safe_eval(selection)
            if not (isinstance(items, (tuple, list)) and
                    all(isinstance(item, (tuple, list)) and len(item) == 2 for item in items)):
                raise ValueError(selection)
        except Exception:
            _logger.info('Invalid selection list definition for fields.selection', exc_info=True)
            raise UserError(_("The Selection Options expression is not a valid Pythonic expression. "
                              "Please provide an expression in the [('key','Label'), ...] format."))

    @api.constrains('name', 'state')
    def _check_name(self):
        for field in self:
            if field.state == 'manual' and not field.name.startswith('x_'):
                raise ValidationError(_("Custom fields must have a name that starts with 'x_' !"))
            try:
                models.check_pg_name(field.name)
            except ValidationError:
                msg = _("Field names can only contain characters, digits and underscores (up to 63).")
                raise ValidationError(msg)

    _sql_constraints = [
        ('name_unique', 'UNIQUE(model, name)', "Field names must be unique per model."),
        ('size_gt_zero', 'CHECK (size>=0)', 'Size of the field cannot be negative.'),
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
                raise ValidationError(_("Related field '%s' does not have type '%s'") % (self.related, self.ttype))
            if field.relational and field.comodel_name != self.relation:
                raise ValidationError(_("Related field '%s' does not have comodel '%s'") % (self.related, self.relation))

    @api.onchange('related')
    def _onchange_related(self):
        if self.related:
            try:
                field = self._related_field()
            except UserError as e:
                return {'warning': {'title': _("Warning"), 'message': e}}
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
        if self.relation_table:
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
            if self.relation not in self.env:
                return {
                    'warning': {
                        'title': _('Model %s does not exist') % self.relation,
                        'message': _('Please specify a valid model for the object relation'),
                    }
                }
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
                return {'warning': {
                    'title': _("Warning"),
                    'message': _("The table %r if used for other, possibly incompatible fields.") % self.relation_table,
                }}

    def _get(self, model_name, name):
        """ Return the (sudoed) `ir.model.fields` record with the given model and name.
        The result may be an empty recordset if the model is not found.
        """
        field_id = self._get_id(model_name, name) if model_name and name else False
        return self.sudo().browse(field_id)

    @tools.ormcache('model_name', 'name')
    def _get_id(self, model_name, name):
        self.env.cr.execute("SELECT id FROM ir_model_fields WHERE model=%s AND name=%s",
                            (model_name, name))
        result = self.env.cr.fetchone()
        return result and result[0]

    @api.multi
    def _drop_column(self):
        tables_to_drop = set()

        for field in self:
            if field.name in models.MAGIC_COLUMNS:
                continue
            model = self.env[field.model]
            if tools.column_exists(self._cr, model._table, field.name) and \
                    tools.table_kind(self._cr, model._table) == 'r':
                self._cr.execute('ALTER TABLE "%s" DROP COLUMN "%s" CASCADE' % (model._table, field.name))
            if field.state == 'manual' and field.ttype == 'many2many':
                rel_name = field.relation_table or model._fields[field.name].relation
                tables_to_drop.add(rel_name)
            if field.state == 'manual':
                model._pop_field(field.name)

        if tables_to_drop:
            # drop the relation tables that are not used by other fields
            self._cr.execute("""SELECT relation_table FROM ir_model_fields
                                WHERE relation_table IN %s AND id NOT IN %s""",
                             (tuple(tables_to_drop), tuple(self.ids)))
            tables_to_keep = set(row[0] for row in self._cr.fetchall())
            for rel_name in tables_to_drop - tables_to_keep:
                self._cr.execute('DROP TABLE "%s"' % rel_name)

        return True

    @api.multi
    def _prepare_update(self):
        """ Check whether the fields in ``self`` may be modified or removed.
            This method prevents the modification/deletion of many2one fields
            that have an inverse one2many, for instance.
        """
        self = self.filtered(lambda record: record.state == 'manual')
        if not self:
            return

        for record in self:
            model = self.env[record.model]
            field = model._fields[record.name]
            if field.type == 'many2one' and model._field_inverses.get(field):
                if self._context.get(MODULE_UNINSTALL_FLAG):
                    # automatically unlink the corresponding one2many field(s)
                    inverses = self.search([('relation', '=', field.model_name),
                                            ('relation_field', '=', field.name)])
                    inverses.unlink()
                    continue
                msg = _("The field '%s' cannot be removed because the field '%s' depends on it.")
                raise UserError(msg % (field, model._field_inverses[field][0]))

        # remove fields from registry, and check that views are not broken
        fields = [self.env[record.model]._pop_field(record.name) for record in self]
        domain = expression.OR([('arch_db', 'like', record.name)] for record in self)
        views = self.env['ir.ui.view'].search(domain)
        try:
            for view in views:
                view._check_xml()
        except Exception:
            raise UserError("\n".join([
                _("Cannot rename/delete fields that are still present in views:"),
                _("Fields: %s") % ", ".join(str(f) for f in fields),
                _("View: %s") % view.name,
            ]))
        finally:
            # the registry has been modified, restore it
            self.pool.setup_models(self._cr)

    @api.multi
    def unlink(self):
        if not self:
            return True

        # Prevent manual deletion of module columns
        if not self._context.get(MODULE_UNINSTALL_FLAG) and \
                any(field.state != 'manual' for field in self):
            raise UserError(_("This column contains module data and cannot be removed!"))

        # prevent screwing up fields that depend on these fields
        self._prepare_update()

        model_names = self.mapped('model')
        self._drop_column()
        res = super(IrModelFields, self).unlink()

        # The field we just deleted might be inherited, and the registry is
        # inconsistent in this case; therefore we reload the registry.
        if not self._context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this re-initializes models in registry
            self.pool.setup_models(self._cr)
            # update database schema of model and its descendant models
            models = self.pool.descendants(model_names, '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

        return res

    @api.model
    def create(self, vals):
        if 'model_id' in vals:
            model_data = self.env['ir.model'].browse(vals['model_id'])
            vals['model'] = model_data.model
        if vals.get('ttype') == 'selection':
            if not vals.get('selection'):
                raise UserError(_('For selection fields, the Selection Options must be given!'))
            self._check_selection(vals['selection'])

        res = super(IrModelFields, self).create(vals)

        if vals.get('state', 'manual') == 'manual':
            if vals.get('relation') and not self.env['ir.model'].search([('model', '=', vals['relation'])]):
                raise UserError(_("Model %s does not exist!") % vals['relation'])

            if vals.get('ttype') == 'one2many':
                if not self.search([('model_id', '=', vals['relation']), ('name', '=', vals['relation_field']), ('ttype', '=', 'many2one')]):
                    raise UserError(_("Many2one %s on model %s does not exist!") % (vals['relation_field'], vals['relation']))

            self.clear_caches()                     # for _existing_field_data()

            if vals['model'] in self.pool:
                # setup models; this re-initializes model in registry
                self.pool.setup_models(self._cr)
                # update database schema of model and its descendant models
                models = self.pool.descendants([vals['model']], '_inherits')
                self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

        return res

    @api.multi
    def write(self, vals):
        # if set, *one* column can be renamed here
        column_rename = None

        # names of the models to patch
        patched_models = set()

        if vals and self:
            # check selection if given
            if vals.get('selection'):
                self._check_selection(vals['selection'])

            for item in self:
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
                    column_rename = (obj._table, item.name, vals['name'], item.index)

                # We don't check the 'state', because it might come from the context
                # (thus be set for multiple fields) and will be ignored anyway.
                if obj is not None and field is not None:
                    patched_models.add(obj._name)

        # These shall never be written (modified)
        for column_name in ('model_id', 'model', 'state'):
            if column_name in vals:
                del vals[column_name]

        res = super(IrModelFields, self).write(vals)

        self.clear_caches()                         # for _existing_field_data()

        if column_rename:
            # rename column in database, and its corresponding index if present
            table, oldname, newname, index = column_rename
            self._cr.execute('ALTER TABLE "%s" RENAME COLUMN "%s" TO "%s"' % (table, oldname, newname))
            if index:
                self._cr.execute('ALTER INDEX "%s_%s_index" RENAME TO "%s_%s_index"' % (table, oldname, table, newname))

        if column_rename or patched_models:
            # setup models, this will reload all manual fields in registry
            self.pool.setup_models(self._cr)

        if patched_models:
            # update the database schema of the models to patch
            models = self.pool.descendants(patched_models, '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

        return res

    @api.multi
    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s (%s)' % (field.field_description, field.model)))
        return res

    @tools.ormcache('model_name')
    def _existing_field_data(self, model_name):
        """ Return the given model's existing field data. """
        cr = self._cr
        cr.execute("SELECT * FROM ir_model_fields WHERE model=%s", [model_name])
        return {row['name']: row for row in cr.dictfetchall()}

    def _reflect_field_params(self, field):
        """ Return the values to write to the database for the given field. """
        model = self.env['ir.model']._get(field.model_name)
        return {
            'model_id': model.id,
            'model': field.model_name,
            'name': field.name,
            'field_description': field.string,
            'help': field.help or None,
            'ttype': field.type,
            'state': 'manual' if field.manual else 'base',
            'relation': field.comodel_name or None,
            'index': bool(field.index),
            'store': bool(field.store),
            'copy': bool(field.copy),
            'related': ".".join(field.related) if field.related else None,
            'readonly': bool(field.readonly),
            'required': bool(field.required),
            'selectable': bool(field.search or field.store),
            'translate': bool(field.translate),
            'relation_field': field.inverse_name if field.type == 'one2many' else None,
            'relation_table': field.relation if field.type == 'many2many' else None,
            'column1': field.column1 if field.type == 'many2many' else None,
            'column2': field.column2 if field.type == 'many2many' else None,
        }

    def _reflect_field(self, field):
        """ Reflect the given field and return its corresponding record. """
        fields_data = self._existing_field_data(field.model_name)
        field_data = fields_data.get(field.name)
        params = self._reflect_field_params(field)

        if field_data is None:
            cr = self.env.cr
            # create an entry in this table
            query_insert(cr, self._table, params)
            record = self.browse(cr.fetchone())
            self.pool.post_init(record.modified, list(params))
            # create a corresponding xml id
            module = field._module or self._context.get('module')
            if module:
                model = self.env[field.model_name]
                xmlid = 'field_%s_%s' % (model._table, field.name)
                cr.execute("SELECT name FROM ir_model_data WHERE name=%s", (xmlid,))
                if cr.fetchone():
                    xmlid = xmlid + "_" + str(record.id)
                cr.execute(""" INSERT INTO ir_model_data (module, name, model, res_id, date_init, date_update)
                               VALUES (%s, %s, %s, %s, (now() at time zone 'UTC'), (now() at time zone 'UTC')) """,
                           (module, xmlid, record._name, record.id))
            # update fields_data (for recursive calls)
            fields_data[field.name] = dict(params, id=record.id)
            return record

        diff = {key for key, val in params.items() if field_data[key] != val}
        if diff:
            cr = self.env.cr
            # update the entry in this table
            query_update(cr, self._table, params, ['model', 'name'])
            record = self.browse(cr.fetchone())
            self.pool.post_init(record.modified, diff)
            # update fields_data (for recursive calls)
            field_data.update(params)
            return record

        else:
            # nothing to update, simply return the corresponding record
            return self.browse(field_data['id'])

    def _reflect_model(self, model):
        """ Reflect the given model's fields. """
        self.clear_caches()
        for field in model._fields.values():
            self._reflect_field(field)

        if not self.pool._init:
            # remove ir.model.fields that are not in self._fields
            fields_data = self._existing_field_data(model._name)
            extra_names = set(fields_data) - set(model._fields)
            if extra_names:
                # add key MODULE_UNINSTALL_FLAG in context to (1) force the
                # removal of the fields and (2) not reload the registry
                records = self.browse([fields_data.pop(name)['id'] for name in extra_names])
                records.with_context(**{MODULE_UNINSTALL_FLAG: True}).unlink()

    @tools.ormcache()
    def _all_manual_field_data(self):
        cr = self._cr
        cr.execute("SELECT * FROM ir_model_fields WHERE state='manual'")
        result = defaultdict(dict)
        for row in cr.dictfetchall():
            result[row['model']][row['name']] = row
        return result

    def _get_manual_field_data(self, model_name):
        """ Return the given model's manual field data. """
        return self._all_manual_field_data().get(model_name, {})

    def _instanciate_attrs(self, field_data):
        """ Return the parameters for a field instance for ``field_data``. """
        attrs = {
            'manual': True,
            'string': field_data['field_description'],
            'help': field_data['help'],
            'index': bool(field_data['index']),
            'copy': bool(field_data['copy']),
            'related': field_data['related'],
            'required': bool(field_data['required']),
            'readonly': bool(field_data['readonly']),
            'store': bool(field_data['store']),
        }
        if field_data['ttype'] in ('char', 'text', 'html'):
            attrs['translate'] = bool(field_data['translate'])
            attrs['size'] = field_data['size'] or None
        elif field_data['ttype'] in ('selection', 'reference'):
            attrs['selection'] = safe_eval(field_data['selection'])
        elif field_data['ttype'] == 'many2one':
            if not self.pool.loaded and field_data['relation'] not in self.env:
                return
            attrs['comodel_name'] = field_data['relation']
            attrs['ondelete'] = field_data['on_delete']
            attrs['domain'] = safe_eval(field_data['domain'] or '[]')
        elif field_data['ttype'] == 'one2many':
            if not self.pool.loaded and not (
                field_data['relation'] in self.env and (
                    field_data['relation_field'] in self.env[field_data['relation']]._fields or
                    field_data['relation_field'] in self._get_manual_field_data(field_data['relation'])
            )):
                return
            attrs['comodel_name'] = field_data['relation']
            attrs['inverse_name'] = field_data['relation_field']
            attrs['domain'] = safe_eval(field_data['domain'] or '[]')
        elif field_data['ttype'] == 'many2many':
            if not self.pool.loaded and field_data['relation'] not in self.env:
                return
            attrs['comodel_name'] = field_data['relation']
            rel, col1, col2 = self._custom_many2many_names(field_data['model'], field_data['relation'])
            attrs['relation'] = field_data['relation_table'] or rel
            attrs['column1'] = field_data['column1'] or col1
            attrs['column2'] = field_data['column2'] or col2
            attrs['domain'] = safe_eval(field_data['domain'] or '[]')
        elif field_data['ttype'] == 'monetary' and not self.pool.loaded:
            return
        # add compute function if given
        if field_data['compute']:
            attrs['compute'] = make_compute(field_data['compute'], field_data['depends'])
        return attrs

    def _instanciate(self, field_data):
        """ Return a field instance corresponding to parameters ``field_data``. """
        attrs = self._instanciate_attrs(field_data)
        if attrs:
            return fields.Field.by_type[field_data['ttype']](**attrs)

    def _add_manual_fields(self, model):
        """ Add extra fields on model. """
        fields_data = self._get_manual_field_data(model._name)
        for name, field_data in fields_data.items():
            if name not in model._fields and field_data['state'] == 'manual':
                field = self._instanciate(field_data)
                if field:
                    model._add_field(name, field)


class IrModelConstraint(models.Model):
    """
    This model tracks PostgreSQL foreign keys and constraints used by Odoo
    models.
    """
    _name = 'ir.model.constraint'

    name = fields.Char(string='Constraint', required=True, index=True,
                       help="PostgreSQL constraint or foreign key name.")
    definition = fields.Char(help="PostgreSQL constraint definition")
    model = fields.Many2one('ir.model', required=True, ondelete="cascade", index=True)
    module = fields.Many2one('ir.module.module', required=True, index=True)
    type = fields.Char(string='Constraint Type', required=True, size=1, index=True,
                       help="Type of the constraint: `f` for a foreign key, "
                            "`u` for other constraints.")
    date_update = fields.Datetime(string='Update Date')
    date_init = fields.Datetime(string='Initialization Date')

    _sql_constraints = [
        ('module_name_uniq', 'unique(name, module)',
         'Constraints with the same name are unique per module.'),
    ]

    @api.multi
    def _module_data_uninstall(self):
        """
        Delete PostgreSQL foreign keys and constraints tracked by this model.
        """
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            raise AccessError(_('Administrator access is required to uninstall a module'))

        ids_set = set(self.ids)
        for data in self.sorted(key='id', reverse=True):
            name = tools.ustr(data.name)
            if data.model.model in self.env:
                table = self.env[data.model.model]._table    
            else:
                table = data.model.model.replace('.', '_')
            typ = data.type

            # double-check we are really going to delete all the owners of this schema element
            self._cr.execute("""SELECT id from ir_model_constraint where name=%s""", (data.name,))
            external_ids = set(x[0] for x in self._cr.fetchall())
            if external_ids - ids_set:
                # as installed modules have defined this element we must not delete it!
                continue

            if typ == 'f':
                # test if FK exists on this table (it could be on a related m2m table, in which case we ignore it)
                self._cr.execute("""SELECT 1 from pg_constraint cs JOIN pg_class cl ON (cs.conrelid = cl.oid)
                                    WHERE cs.contype=%s and cs.conname=%s and cl.relname=%s""",
                                 ('f', name, table))
                if self._cr.fetchone():
                    self._cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (table, name),)
                    _logger.info('Dropped FK CONSTRAINT %s@%s', name, data.model.model)

            if typ == 'u':
                # test if constraint exists
                self._cr.execute("""SELECT 1 from pg_constraint cs JOIN pg_class cl ON (cs.conrelid = cl.oid)
                                    WHERE cs.contype=%s and cs.conname=%s and cl.relname=%s""",
                                 ('u', name, table))
                if self._cr.fetchone():
                    self._cr.execute('ALTER TABLE "%s" DROP CONSTRAINT "%s"' % (table, name),)
                    _logger.info('Dropped CONSTRAINT %s@%s', name, data.model.model)

        self.unlink()

    @api.multi
    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.name + '_copy'
        return super(IrModelConstraint, self).copy(default)

    def _reflect_constraint(self, model, conname, type, definition, module):
        """ Reflect the given constraint, to make it possible to delete it later
            when the module is uninstalled. ``type`` is either 'f' or 'u'
            depending on the constraint being a foreign key or not.
        """
        if not module:
            # no need to save constraints for custom models as they're not part
            # of any module
            return
        assert type in ('f', 'u')
        cr = self._cr
        query = """ SELECT type, definition
                    FROM ir_model_constraint c, ir_module_module m
                    WHERE c.module=m.id AND c.name=%s AND m.name=%s """
        cr.execute(query, (conname, module))
        cons = cr.dictfetchone()
        if not cons:
            query = """ INSERT INTO ir_model_constraint
                            (name, date_init, date_update, module, model, type, definition)
                        VALUES (%s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                            (SELECT id FROM ir_module_module WHERE name=%s),
                            (SELECT id FROM ir_model WHERE model=%s), %s, %s) """
            cr.execute(query, (conname, module, model._name, type, definition))
        elif cons['type'] != type or (definition and cons['definition'] != definition):
            query = """ UPDATE ir_model_constraint
                        SET date_update=now() AT TIME ZONE 'UTC', type=%s, definition=%s
                        WHERE name=%s AND module=(SELECT id FROM ir_module_module WHERE name=%s) """
            cr.execute(query, (type, definition, conname, module))

    def _reflect_model(self, model):
        """ Reflect the _sql_constraints of the given model. """
        def cons_text(txt):
            return txt.lower().replace(', ',',').replace(' (','(')

        # map each constraint on the name of the module where it is defined
        constraint_module = {
            constraint[0]: cls._module
            for cls in reversed(type(model).mro())
            if not getattr(cls, 'pool', None)
            for constraint in getattr(cls, '_local_sql_constraints', ())
        }

        for (key, definition, _) in model._sql_constraints:
            conname = '%s_%s' % (model._table, key)
            module = constraint_module.get(key)
            self._reflect_constraint(model, conname, 'u', cons_text(definition), module)


class IrModelRelation(models.Model):
    """
    This model tracks PostgreSQL tables used to implement Odoo many2many
    relations.
    """
    _name = 'ir.model.relation'

    name = fields.Char(string='Relation Name', required=True, index=True,
                       help="PostgreSQL table name implementing a many2many relation.")
    model = fields.Many2one('ir.model', required=True, index=True)
    module = fields.Many2one('ir.module.module', required=True, index=True)
    date_update = fields.Datetime(string='Update Date')
    date_init = fields.Datetime(string='Initialization Date')

    @api.multi
    def _module_data_uninstall(self):
        """
        Delete PostgreSQL many2many relations tracked by this model.
        """
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            raise AccessError(_('Administrator access is required to uninstall a module'))

        ids_set = set(self.ids)
        to_drop = tools.OrderedSet()
        for data in self.sorted(key='id', reverse=True):
            name = tools.ustr(data.name)

            # double-check we are really going to delete all the owners of this schema element
            self._cr.execute("""SELECT id from ir_model_relation where name = %s""", (data.name,))
            external_ids = set(x[0] for x in self._cr.fetchall())
            if external_ids - ids_set:
                # as installed modules have defined this element we must not delete it!
                continue

            if tools.table_exists(self._cr, name):
                to_drop.add(name)

        self.unlink()

        # drop m2m relation tables
        for table in to_drop:
            self._cr.execute('DROP TABLE "%s" CASCADE' % table,)
            _logger.info('Dropped table %s', table)

    def _reflect_relation(self, model, table, module):
        """ Reflect the table of a many2many field for the given model, to make
            it possible to delete it later when the module is uninstalled.
        """
        cr = self._cr
        query = """ SELECT 1 FROM ir_model_relation r, ir_module_module m
                    WHERE r.module=m.id AND r.name=%s AND m.name=%s """
        cr.execute(query, (table, module))
        if not cr.rowcount:
            query = """ INSERT INTO ir_model_relation (name, date_init, date_update, module, model)
                        VALUES (%s, now() AT TIME ZONE 'UTC', now() AT TIME ZONE 'UTC',
                                (SELECT id FROM ir_module_module WHERE name=%s),
                                (SELECT id FROM ir_model WHERE model=%s)) """
            cr.execute(query, (table, module, model._name))
            self.invalidate_cache()


class IrModelAccess(models.Model):
    _name = 'ir.model.access'

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True, help='If you uncheck the active field, it will disable the ACL without deleting it (if you delete a native ACL, it will be re-created when you reload the module).')
    model_id = fields.Many2one('ir.model', string='Object', required=True, domain=[('transient', '=', False)], index=True, ondelete='cascade')
    group_id = fields.Many2one('res.groups', string='Group', ondelete='cascade', index=True)
    perm_read = fields.Boolean(string='Read Access')
    perm_write = fields.Boolean(string='Write Access')
    perm_create = fields.Boolean(string='Create Access')
    perm_unlink = fields.Boolean(string='Delete Access')

    @api.model
    def check_groups(self, group):
        """ Check whether the current user has the given group. """
        grouparr = group.split('.')
        if not grouparr:
            return False
        self._cr.execute("""SELECT 1 FROM res_groups_users_rel
                            WHERE uid=%s AND gid IN (
                                SELECT res_id FROM ir_model_data WHERE module=%s AND name=%s)""",
                         (self._uid, grouparr[0], grouparr[1],))
        return bool(self._cr.fetchone())

    @api.model
    def check_group(self, model, mode, group_ids):
        """ Check if a specific group has the access mode to the specified model"""
        assert mode in ('read', 'write', 'create', 'unlink'), 'Invalid access mode'

        if isinstance(model, models.BaseModel):
            assert model._name == 'ir.model', 'Invalid model object'
            model_name = model.name
        else:
            model_name = model

        if isinstance(group_ids, pycompat.integer_types):
            group_ids = [group_ids]

        query = """ SELECT 1 FROM ir_model_access a
                    JOIN ir_model m ON (m.id = a.model_id)
                    WHERE a.active AND a.perm_{mode} AND
                        m.model=%s AND (a.group_id IN %s OR a.group_id IS NULL)
                """.format(mode=mode)
        self._cr.execute(query, (model_name, tuple(group_ids)))
        return bool(self._cr.rowcount)

    @api.model_cr
    def group_names_with_access(self, model_name, access_mode):
        """ Return the names of visible groups which have been granted
            ``access_mode`` on the model ``model_name``.
           :rtype: list
        """
        assert access_mode in ('read', 'write', 'create', 'unlink'), 'Invalid access mode'
        self._cr.execute("""SELECT c.name, g.name
                            FROM ir_model_access a
                                JOIN ir_model m ON (a.model_id=m.id)
                                JOIN res_groups g ON (a.group_id=g.id)
                                LEFT JOIN ir_module_category c ON (c.id=g.category_id)
                            WHERE m.model=%s AND a.active IS TRUE AND a.perm_""" + access_mode,
                         (model_name,))
        return [('%s/%s' % x) if x[0] else x[1] for x in self._cr.fetchall()]

    # The context parameter is useful when the method translates error messages.
    # But as the method raises an exception in that case,  the key 'lang' might
    # not be really necessary as a cache key, unless the `ormcache_context`
    # decorator catches the exception (it does not at the moment.)
    @api.model
    @tools.ormcache_context('self._uid', 'model', 'mode', 'raise_exception', keys=('lang',))
    def check(self, model, mode='read', raise_exception=True):
        if self._uid == 1:
            # User root have all accesses
            return True

        assert isinstance(model, pycompat.string_types), 'Not a model name: %s' % (model,)
        assert mode in ('read', 'write', 'create', 'unlink'), 'Invalid access mode'

        # TransientModel records have no access rights, only an implicit access rule
        if model not in self.env:
            _logger.error('Missing model %s', model)
        elif self.env[model].is_transient():
            return True

        # We check if a specific rule exists
        self._cr.execute("""SELECT MAX(CASE WHEN perm_{mode} THEN 1 ELSE 0 END)
                              FROM ir_model_access a
                              JOIN ir_model m ON (m.id = a.model_id)
                              JOIN res_groups_users_rel gu ON (gu.gid = a.group_id)
                             WHERE m.model = %s
                               AND gu.uid = %s
                               AND a.active IS TRUE""".format(mode=mode),
                         (model, self._uid,))
        r = self._cr.fetchone()[0]

        if not r:
            # there is no specific rule. We check the generic rule
            self._cr.execute("""SELECT MAX(CASE WHEN perm_{mode} THEN 1 ELSE 0 END)
                                  FROM ir_model_access a
                                  JOIN ir_model m ON (m.id = a.model_id)
                                 WHERE a.group_id IS NULL
                                   AND m.model = %s
                                   AND a.active IS TRUE""".format(mode=mode),
                             (model,))
            r = self._cr.fetchone()[0]

        if not r and raise_exception:
            groups = '\n\t'.join('- %s' % g for g in self.group_names_with_access(model, mode))
            msg_heads = {
                # Messages are declared in extenso so they are properly exported in translation terms
                'read': _("Sorry, you are not allowed to access this document."),
                'write':  _("Sorry, you are not allowed to modify this document."),
                'create': _("Sorry, you are not allowed to create this kind of document."),
                'unlink': _("Sorry, you are not allowed to delete this document."),
            }
            if groups:
                msg_tail = _("Only users with the following access level are currently allowed to do that") + ":\n%s\n\n(" + _("Document model") + ": %s)"
                msg_params = (groups, model)
            else:
                msg_tail = _("Please contact your system administrator if you think this is an error.") + "\n\n(" + _("Document model") + ": %s)"
                msg_params = (model,)
            _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s', mode, self._uid, model)
            msg = '%s %s' % (msg_heads[mode], msg_tail)
            raise AccessError(msg % msg_params)

        return bool(r)

    __cache_clearing_methods = set()

    @classmethod
    def register_cache_clearing_method(cls, model, method):
        cls.__cache_clearing_methods.add((model, method))

    @classmethod
    def unregister_cache_clearing_method(cls, model, method):
        cls.__cache_clearing_methods.discard((model, method))

    @api.model_cr
    def call_cache_clearing_methods(self):
        self.invalidate_cache()
        self.check.clear_cache(self)    # clear the cache of check function
        for model, method in self.__cache_clearing_methods:
            if model in self.env:
                getattr(self.env[model], method)()

    #
    # Check rights on actions
    #
    @api.model
    def create(self, values):
        self.call_cache_clearing_methods()
        return super(IrModelAccess, self).create(values)

    @api.multi
    def write(self, values):
        self.call_cache_clearing_methods()
        return super(IrModelAccess, self).write(values)

    @api.multi
    def unlink(self):
        self.call_cache_clearing_methods()
        return super(IrModelAccess, self).unlink()


class IrModelData(models.Model):
    """Holds external identifier keys for records in the database.
       This has two main uses:

           * allows easy data integration with third-party systems,
             making import/export/sync of data possible, as records
             can be uniquely identified across multiple systems
           * allows tracking the origin of data installed by Odoo
             modules themselves, thus making it possible to later
             update them seamlessly.
    """
    _name = 'ir.model.data'
    _order = 'module, model, name'

    name = fields.Char(string='External Identifier', required=True,
                       help="External Key/Identifier that can be used for "
                            "data integration with third-party systems")
    complete_name = fields.Char(compute='_compute_complete_name', string='Complete ID')
    model = fields.Char(string='Model Name', required=True)
    module = fields.Char(default='', required=True)
    res_id = fields.Integer(string='Record ID', help="ID of the target record in the database")
    noupdate = fields.Boolean(string='Non Updatable', default=False)
    date_update = fields.Datetime(string='Update Date', default=fields.Datetime.now)
    date_init = fields.Datetime(string='Init Date', default=fields.Datetime.now)
    reference = fields.Char(string='Reference', compute='_compute_reference', readonly=True, store=False)

    @api.depends('module', 'name')
    def _compute_complete_name(self):
        for res in self:
            res.complete_name = ".".join(n for n in [res.module, res.name] if n)

    @api.depends('model', 'res_id')
    def _compute_reference(self):
        for res in self:
            res.reference = "%s,%s" % (res.model, res.res_id)

    def __init__(self, pool, cr):
        models.Model.__init__(self, pool, cr)
        # also stored in pool to avoid being discarded along with this osv instance
        if getattr(pool, 'model_data_reference_ids', None) is None:
            self.pool.model_data_reference_ids = {}
        # put loads on the class, in order to share it among all instances
        type(self).loads = self.pool.model_data_reference_ids

    @api.model_cr_context
    def _auto_init(self):
        res = super(IrModelData, self)._auto_init()
        tools.create_unique_index(self._cr, 'ir_model_data_module_name_uniq_index',
                                  self._table, ['module', 'name'])
        tools.create_index(self._cr, 'ir_model_data_model_res_id_index',
                           self._table, ['model', 'res_id'])
        return res

    @api.multi
    def name_get(self):
        model_id_name = defaultdict(dict)       # {res_model: {res_id: name}}
        for xid in self:
            model_id_name[xid.model][xid.res_id] = None

        # fill in model_id_name with name_get() of corresponding records
        for model, id_name in model_id_name.items():
            try:
                ng = self.env[model].browse(id_name).name_get()
                id_name.update(ng)
            except Exception:
                pass

        # return results, falling back on complete_name
        return [(xid.id, model_id_name[xid.model][xid.res_id] or xid.complete_name)
                for xid in self]

    # NEW V8 API
    @api.model
    @tools.ormcache('xmlid')
    def xmlid_lookup(self, xmlid):
        """Low level xmlid lookup
        Return (id, res_model, res_id) or raise ValueError if not found
        """
        module, name = xmlid.split('.', 1)
        xid = self.sudo().search([('module', '=', module), ('name', '=', name)])
        if not xid:
            raise ValueError('External ID not found in the system: %s' % xmlid)
        # the sql constraints ensure us we have only one result
        res = xid.read(['model', 'res_id'])[0]
        if not res['res_id']:
            raise ValueError('External ID not found in the system: %s' % xmlid)
        return res['id'], res['model'], res['res_id']

    @api.model
    def xmlid_to_res_model_res_id(self, xmlid, raise_if_not_found=False):
        """ Return (res_model, res_id)"""
        try:
            return self.xmlid_lookup(xmlid)[1:3]
        except ValueError:
            if raise_if_not_found:
                raise
            return (False, False)

    @api.model
    def xmlid_to_res_id(self, xmlid, raise_if_not_found=False):
        """ Returns res_id """
        return self.xmlid_to_res_model_res_id(xmlid, raise_if_not_found)[1]

    @api.model
    def xmlid_to_object(self, xmlid, raise_if_not_found=False):
        """ Return a Model object, or ``None`` if ``raise_if_not_found`` is 
        set
        """
        t = self.xmlid_to_res_model_res_id(xmlid, raise_if_not_found)
        res_model, res_id = t

        if res_model and res_id:
            record = self.env[res_model].browse(res_id)
            if record.exists():
                return record
            if raise_if_not_found:
                raise ValueError('No record found for unique ID %s. It may have been deleted.' % (xmlid))
        return None

    @api.model
    def _get_id(self, module, xml_id):
        """Returns the id of the ir.model.data record corresponding to a given module and xml_id (cached) or raise a ValueError if not found"""
        return self.xmlid_lookup("%s.%s" % (module, xml_id))[0]

    @api.model
    def get_object_reference(self, module, xml_id):
        """Returns (model, res_id) corresponding to a given module and xml_id (cached) or raise ValueError if not found"""
        return self.xmlid_lookup("%s.%s" % (module, xml_id))[1:3]

    @api.model
    def check_object_reference(self, module, xml_id, raise_on_access_error=False):
        """Returns (model, res_id) corresponding to a given module and xml_id (cached), if and only if the user has the necessary access rights
        to see that object, otherwise raise a ValueError if raise_on_access_error is True or returns a tuple (model found, False)"""
        model, res_id = self.get_object_reference(module, xml_id)
        #search on id found in result to check if current user has read access right
        if self.env[model].search([('id', '=', res_id)]):
            return model, res_id
        if raise_on_access_error:
            raise AccessError('Not enough access rights on the external ID: %s.%s' % (module, xml_id))
        return model, False

    @api.model
    def get_object(self, module, xml_id):
        """ Returns a browsable record for the given module name and xml_id.
            If not found, raise a ValueError or return None, depending
            on the value of `raise_exception`.
        """
        return self.xmlid_to_object("%s.%s" % (module, xml_id), raise_if_not_found=True)

    @api.model
    def _update_dummy(self, model, module, xml_id=False, store=True):
        if xml_id:
            try:
                # One step to check the ID is defined and the record actually exists
                record = self.get_object(module, xml_id)
                if record:
                    self.loads[(module, xml_id)] = (model, record.id)
                    for parent_model, parent_field in self.env[model]._inherits.items():
                        parent = record[parent_field]
                        parent_xid = '%s_%s' % (xml_id, parent_model.replace('.', '_'))
                        self.loads[(module, parent_xid)] = (parent_model, parent.id)
                return record.id
            except Exception:
                pass
        return False

    @api.multi
    def unlink(self):
        """ Regular unlink method, but make sure to clear the caches. """
        self.clear_caches()
        return super(IrModelData, self).unlink()

    @api.model
    def _update(self, model, module, values, xml_id=False, store=True, noupdate=False, mode='init', res_id=False):
        # records created during module install should not display the messages of OpenChatter
        self = self.with_context(install_mode=True)
        current_module = module

        if xml_id and ('.' in xml_id):
            assert len(xml_id.split('.')) == 2, _("'%s' contains too many dots. XML ids should not contain dots ! These are used to refer to other modules data, as in module.reference_id") % xml_id
            module, xml_id = xml_id.split('.')

        action = self.browse()
        record = self.env[model].browse(res_id)

        if xml_id:
            self._cr.execute("""SELECT imd.id, imd.res_id, md.id, imd.model, imd.noupdate
                                FROM ir_model_data imd LEFT JOIN %s md ON (imd.res_id = md.id)
                                WHERE imd.module=%%s AND imd.name=%%s""" % record._table,
                             (module, xml_id))
            results = self._cr.fetchall()
            for imd_id, imd_res_id, real_id, imd_model, imd_noupdate in results:
                # In update mode, do not update a record if it's ir.model.data is flagged as noupdate
                if mode == 'update' and imd_noupdate:
                    return imd_res_id
                if not real_id:
                    self.clear_caches()
                    self._cr.execute('DELETE FROM ir_model_data WHERE id=%s', (imd_id,))
                    record = record.browse()
                else:
                    assert model == imd_model, "External ID conflict, %s already refers to a `%s` record,"\
                        " you can't define a `%s` record with this ID." % (xml_id, imd_model, model)
                    action = self.browse(imd_id)
                    record = record.browse(imd_res_id)

        if action and record:
            record.write(values)
            action.sudo().write({'date_update': fields.Datetime.now()})

        elif record:
            record.write(values)
            if xml_id:
                for parent_model, parent_field in record._inherits.items():
                    self.sudo().create({
                        'name': xml_id + '_' + parent_model.replace('.', '_'),
                        'model': parent_model,
                        'module': module,
                        'res_id': record[parent_field].id,
                        'noupdate': noupdate,
                    })
                self.sudo().create({
                    'name': xml_id,
                    'model': model,
                    'module': module,
                    'res_id': record.id,
                    'noupdate': noupdate,
                })

        elif mode == 'init' or (mode == 'update' and xml_id):
            existing_parents = set()            # {parent_model, ...}
            if xml_id:
                for parent_model, parent_field in record._inherits.items():
                    xid = self.sudo().search([
                        ('module', '=', module),
                        ('name', '=', xml_id + '_' + parent_model.replace('.', '_')),
                    ])
                    # XML ID found in the database, try to recover an existing record
                    if xid:
                        parent = self.env[xid.model].browse(xid.res_id)
                        if parent.exists():
                            existing_parents.add(xid.model)
                            values[parent_field] = parent.id
                        else:
                            xid.unlink()

            record = record.create(values)
            if xml_id:
                #To add an external identifiers to all inherits model
                inherit_models = [record]
                while inherit_models:
                    current_model = inherit_models.pop()
                    for parent_model_name, parent_field in current_model._inherits.items():
                        inherit_models.append(self.env[parent_model_name])
                        if parent_model_name in existing_parents:
                            continue
                        self.sudo().create({
                            'name': xml_id + '_' + parent_model_name.replace('.', '_'),
                            'model': parent_model_name,
                            'module': module,
                            'res_id': record[parent_field].id,
                            'noupdate': noupdate,
                        })
                        existing_parents.add(parent_model_name)
                self.sudo().create({
                    'name': xml_id,
                    'model': model,
                    'module': module,
                    'res_id': record.id,
                    'noupdate': noupdate
                })
                if current_module and module != current_module:
                    _logger.warning("Creating the ir.model.data %s in module %s instead of %s.",
                                    xml_id, module, current_module)


        if xml_id and record:
            self.loads[(module, xml_id)] = (model, record.id)
            for parent_model, parent_field in record._inherits.items():
                parent_xml_id = xml_id + '_' + parent_model.replace('.', '_')
                self.loads[(module, parent_xml_id)] = (parent_model, record[parent_field].id)

        return record.id

    @api.model
    def _module_data_uninstall(self, modules_to_remove):
        """Deletes all the records referenced by the ir.model.data entries
        ``ids`` along with their corresponding database backed (including
        dropping tables, columns, FKs, etc, as long as there is no other
        ir.model.data entry holding a reference to them (which indicates that
        they are still owned by another module). 
        Attempts to perform the deletion in an appropriate order to maximize
        the chance of gracefully deleting all records.
        This step is performed as part of the full uninstallation of a module.
        """ 
        if not (self._uid == SUPERUSER_ID or self.env.user.has_group('base.group_system')):
            raise AccessError(_('Administrator access is required to uninstall a module'))

        # enable model/field deletion
        self = self.with_context(**{MODULE_UNINSTALL_FLAG: True})

        datas = self.search([('module', 'in', modules_to_remove)])
        to_unlink = tools.OrderedSet()
        undeletable = self.browse([])

        for data in datas.sorted(key='id', reverse=True):
            model = data.model
            res_id = data.res_id
            to_unlink.add((model, res_id))

        def unlink_if_refcount(to_unlink):
            undeletable = self.browse()
            for model, res_id in to_unlink:
                external_ids = self.search([('model', '=', model), ('res_id', '=', res_id)])
                if external_ids - datas:
                    # if other modules have defined this record, we must not delete it
                    continue
                if model == 'ir.model.fields':
                    # Don't remove the LOG_ACCESS_COLUMNS unless _log_access
                    # has been turned off on the model.
                    field = self.env[model].browse(res_id).with_context(
                        prefetch_fields=False,
                    )
                    if not field.exists():
                        _logger.info('Deleting orphan external_ids %s', external_ids)
                        external_ids.unlink()
                        continue
                    if field.name in models.LOG_ACCESS_COLUMNS and field.model in self.env and self.env[field.model]._log_access:
                        continue
                    if field.name == 'id':
                        continue
                _logger.info('Deleting %s@%s', res_id, model)
                try:
                    self._cr.execute('SAVEPOINT record_unlink_save')
                    self.env[model].browse(res_id).unlink()
                except Exception:
                    _logger.info('Unable to delete %s@%s', res_id, model, exc_info=True)
                    undeletable += external_ids
                    self._cr.execute('ROLLBACK TO SAVEPOINT record_unlink_save')
                else:
                    self._cr.execute('RELEASE SAVEPOINT record_unlink_save')
            return undeletable

        # Remove non-model records first, then model fields, and finish with models
        undeletable += unlink_if_refcount(item for item in to_unlink if item[0] not in ('ir.model', 'ir.model.fields', 'ir.model.constraint'))
        undeletable += unlink_if_refcount(item for item in to_unlink if item[0] == 'ir.model.constraint')

        modules = self.env['ir.module.module'].search([('name', 'in', modules_to_remove)])
        constraints = self.env['ir.model.constraint'].search([('module', 'in', modules.ids)])
        constraints._module_data_uninstall()

        undeletable += unlink_if_refcount(item for item in to_unlink if item[0] == 'ir.model.fields')

        relations = self.env['ir.model.relation'].search([('module', 'in', modules.ids)])
        relations._module_data_uninstall()

        undeletable += unlink_if_refcount(item for item in to_unlink if item[0] == 'ir.model')


        (datas - undeletable).unlink()

    @api.model
    def _process_end(self, modules):
        """ Clear records removed from updated module data.
        This method is called at the end of the module loading process.
        It is meant to removed records that are no longer present in the
        updated data. Such records are recognised as the one with an xml id
        and a module in ir_model_data and noupdate set to false, but not
        present in self.loads.
        """
        if not modules or tools.config.get('import_partial'):
            return True

        bad_imd_ids = []
        self = self.with_context({MODULE_UNINSTALL_FLAG: True})

        query = """ SELECT id, name, model, res_id, module FROM ir_model_data
                    WHERE module IN %s AND res_id IS NOT NULL AND noupdate=%s ORDER BY id DESC
                """
        self._cr.execute(query, (tuple(modules), False))
        for (id, name, model, res_id, module) in self._cr.fetchall():
            if (module, name) not in self.loads:
                if model in self.env:
                    _logger.info('Deleting %s@%s (%s.%s)', res_id, model, module, name)
                    record = self.env[model].browse(res_id)
                    if record.exists():
                        record.unlink()
                    else:
                        bad_imd_ids.append(id)
        if bad_imd_ids:
            self.browse(bad_imd_ids).unlink()
        self.loads.clear()


class WizardModelMenu(models.TransientModel):
    _name = 'wizard.ir.model.menu.create'

    menu_id = fields.Many2one('ir.ui.menu', string='Parent Menu', required=True, ondelete='cascade')
    name = fields.Char(string='Menu Name', required=True)

    @api.multi
    def menu_create(self):
        for menu in self:
            model = self.env['ir.model'].browse(self._context.get('model_id'))
            vals = {
                'name': menu.name,
                'res_model': model.model,
                'view_mode': 'tree,form',
            }
            action_id = self.env['ir.actions.act_window'].create(vals)
            self.env['ir.ui.menu'].create({
                'name': menu.name,
                'parent_id': menu.menu_id.id,
                'action': 'ir.actions.act_window,%d' % (action_id,)
            })
        return {'type': 'ir.actions.act_window_close'}
