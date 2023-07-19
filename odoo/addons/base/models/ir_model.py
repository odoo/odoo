# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import itertools
import logging
import random
import re
import psycopg2
from ast import literal_eval
from collections import defaultdict
from collections.abc import Mapping
from operator import itemgetter

from psycopg2 import sql
from psycopg2.extras import Json

from odoo import api, fields, models, tools, _, _lt, Command
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.osv import expression
from odoo.tools import pycompat, unique, OrderedSet
from odoo.tools.safe_eval import safe_eval, datetime, dateutil, time

_logger = logging.getLogger(__name__)

MODULE_UNINSTALL_FLAG = '_force_unlink'
RE_ORDER_FIELDS = re.compile(r'"?(\w+)"?\s*(?:asc|desc)?', flags=re.I)

# base environment for doing a safe_eval
SAFE_EVAL_BASE = {
    'datetime': datetime,
    'dateutil': dateutil,
    'time': time,
}


def make_compute(text, deps):
    """ Return a compute function from its code body and dependencies. """
    func = lambda self: safe_eval(text, SAFE_EVAL_BASE, {'self': self}, mode="exec")
    deps = [arg.strip() for arg in deps.split(",")] if deps else []
    return api.depends(*deps)(func)


def mark_modified(records, fnames):
    """ Mark the given fields as modified on records. """
    # protect all modified fields, to avoid them being recomputed
    fields = [records._fields[fname] for fname in fnames]
    with records.env.protecting(fields, records):
        records.modified(fnames)


def model_xmlid(module, model_name):
    """ Return the XML id of the given model. """
    return '%s.model_%s' % (module, model_name.replace('.', '_'))


def field_xmlid(module, model_name, field_name):
    """ Return the XML id of the given field. """
    return '%s.field_%s__%s' % (module, model_name.replace('.', '_'), field_name)


def selection_xmlid(module, model_name, field_name, value):
    """ Return the XML id of the given selection. """
    xmodel = model_name.replace('.', '_')
    xvalue = value.replace('.', '_').replace(' ', '_').lower()
    return '%s.selection__%s__%s__%s' % (module, xmodel, field_name, xvalue)


# generic INSERT and UPDATE queries
INSERT_QUERY = "INSERT INTO {table} ({cols}) VALUES {rows} RETURNING id"
UPDATE_QUERY = "UPDATE {table} SET {assignment} WHERE {condition} RETURNING id"

quote = '"{}"'.format


def query_insert(cr, table, rows):
    """ Insert rows in a table. ``rows`` is a list of dicts, all with the same
        set of keys. Return the ids of the new rows.
    """
    if isinstance(rows, Mapping):
        rows = [rows]
    cols = list(rows[0])
    query = INSERT_QUERY.format(
        table='"{}"'.format(table),
        cols=",".join(['"{}"'.format(col) for col in cols]),
        rows=",".join("%s" for row in rows),
    )
    params = [tuple(row[col] for col in cols) for row in rows]
    cr.execute(query, params)
    return [row[0] for row in cr.fetchall()]


def query_update(cr, table, values, selectors):
    """ Update the table with the given values (dict), and use the columns in
        ``selectors`` to select the rows to update.
    """
    setters = set(values) - set(selectors)
    query = UPDATE_QUERY.format(
        table='"{}"'.format(table),
        assignment=",".join('"{0}"=%({0})s'.format(s) for s in setters),
        condition=" AND ".join('"{0}"=%({0})s'.format(s) for s in selectors),
    )
    cr.execute(query, values)
    return [row[0] for row in cr.fetchall()]


def select_en(model, fnames, where, params):
    """ Select the given columns from the given model's table, with the given WHERE clause.
    Translated fields are returned in 'en_US'.
    """
    table = quote(model._table)
    cols = ", ".join(
        f"{quote(fname)}->>'en_US'" if model._fields[fname].translate else quote(fname)
        for fname in fnames
    )
    query = f"SELECT {cols} FROM {table} WHERE {where}"
    model.env.cr.execute(query, params)
    return model.env.cr.fetchall()


def upsert_en(model, fnames, rows, conflict):
    """ Insert or update the table with the given rows.

    :param model: recordset of the model to query
    :param fnames: list of column names
    :param rows: list of tuples, where each tuple value corresponds to a column name
    :param conflict: list of column names to put into the ON CONFLICT clause
    :return: the ids of the inserted or updated rows
    """
    table = quote(model._table)
    cols = ", ".join(quote(fname) for fname in fnames)
    values = ", ".join("%s" for row in rows)
    conf = ", ".join(conflict)
    excluded = ", ".join(f"EXCLUDED.{quote(fname)}" for fname in fnames)
    query = f"""
        INSERT INTO {table} ({cols}) VALUES {values}
        ON CONFLICT ({conf}) DO UPDATE SET ({cols}) = ({excluded})
        RETURNING id
    """

    # for translated fields, we can actually erase the json value, as
    # translations will be reloaded after this
    def identity(val):
        return val

    def jsonify(val):
        return Json({'en_US': val}) if val is not None else val

    wrappers = [(jsonify if model._fields[fname].translate else identity) for fname in fnames]
    params = [
        tuple(func(val) for func, val in zip(wrappers, row))
        for row in rows
    ]
    model.env.cr.execute(query, params)
    return [row[0] for row in model.env.cr.fetchall()]


#
# IMPORTANT: this must be the first model declared in the module
#
class Base(models.AbstractModel):
    """ The base model, which is implicitly inherited by all models. """
    _name = 'base'
    _description = 'Base'


class Unknown(models.AbstractModel):
    """
    Abstract model used as a substitute for relational fields with an unknown
    comodel.
    """
    _name = '_unknown'
    _description = 'Unknown'


class IrModel(models.Model):
    _name = 'ir.model'
    _description = "Models"
    _order = 'model'
    _rec_names_search = ['name', 'model']

    def _default_field_id(self):
        if self.env.context.get('install_mode'):
            return []                   # no default field when importing
        return [Command.create({'name': 'x_name', 'field_description': 'Name', 'ttype': 'char', 'copied': True})]

    name = fields.Char(string='Model Description', translate=True, required=True)
    model = fields.Char(default='x_', required=True)
    order = fields.Char(string='Order', default='id', required=True,
                        help='SQL expression for ordering records in the model; e.g. "x_sequence asc, id desc"')
    info = fields.Text(string='Information')
    field_id = fields.One2many('ir.model.fields', 'model_id', string='Fields', required=True, copy=True,
                               default=_default_field_id)
    inherited_model_ids = fields.Many2many('ir.model', compute='_inherited_models', string="Inherited models",
                                           help="The list of models that extends the current model.")
    state = fields.Selection([('manual', 'Custom Object'), ('base', 'Base Object')], string='Type', default='manual', readonly=True)
    access_ids = fields.One2many('ir.model.access', 'model_id', string='Access')
    rule_ids = fields.One2many('ir.rule', 'model_id', string='Record Rules')
    transient = fields.Boolean(string="Transient Model")
    modules = fields.Char(compute='_in_modules', string='In Apps', help='List of modules in which the object is defined or inherited')
    view_ids = fields.One2many('ir.ui.view', compute='_view_ids', string='Views')
    count = fields.Integer(compute='_compute_count', string="Count (Incl. Archived)",
                           help="Total number of records in this model")

    @api.depends()
    def _inherited_models(self):
        self.inherited_model_ids = False
        for model in self:
            parent_names = list(self.env[model.model]._inherits)
            if parent_names:
                model.inherited_model_ids = self.search([('model', 'in', parent_names)])
            else:
                model.inherited_model_ids = False

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
        self.count = 0
        for model in self:
            records = self.env[model.model]
            if not records._abstract and records._auto:
                cr.execute(sql.SQL('SELECT COUNT(*) FROM {}').format(sql.Identifier(records._table)))
                model.count = cr.fetchone()[0]

    @api.constrains('model')
    def _check_model_name(self):
        for model in self:
            if model.state == 'manual':
                if not model.model.startswith('x_'):
                    raise ValidationError(_("The model name must start with 'x_'."))
            if not models.check_object_name(model.model):
                raise ValidationError(_("The model name can only contain lowercase characters, digits, underscores and dots."))

    @api.constrains('order', 'field_id')
    def _check_order(self):
        for model in self:
            try:
                model._check_qorder(model.order)  # regex check for the whole clause ('is it valid sql?')
            except UserError as e:
                raise ValidationError(str(e))
            # add MAGIC_COLUMNS to 'stored_fields' in case 'model' has not been
            # initialized yet, or 'field_id' is not up-to-date in cache
            stored_fields = set(
                model.field_id.filtered('store').mapped('name') + models.MAGIC_COLUMNS
            )
            order_fields = RE_ORDER_FIELDS.findall(model.order)
            for field in order_fields:
                if field not in stored_fields:
                    raise ValidationError(_("Unable to order by %s: fields used for ordering must be present on the model and stored.", field))

    _sql_constraints = [
        ('obj_name_uniq', 'unique (model)', 'Each model must have a unique name.'),
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

    def _drop_table(self):
        for model in self:
            current_model = self.env.get(model.model)
            if current_model is not None:
                table = current_model._table
                kind = tools.table_kind(self._cr, table)
                if kind == 'v':
                    self._cr.execute(sql.SQL('DROP VIEW {}').format(sql.Identifier(table)))
                elif kind == 'r':
                    self._cr.execute(sql.SQL('DROP TABLE {} CASCADE').format(sql.Identifier(table)))
            else:
                _logger.runbot('The model %s could not be dropped because it did not exist in the registry.', model.model)
        return True

    @api.ondelete(at_uninstall=False)
    def _unlink_if_manual(self):
        # Prevent manual deletion of module tables
        for model in self:
            if model.state != 'manual':
                raise UserError(_("Model '%s' contains module data and cannot be removed.", model.name))

    def unlink(self):
        # prevent screwing up fields that depend on these models' fields
        self.field_id._prepare_update()

        # delete fields whose comodel is being removed
        self.env['ir.model.fields'].search([('relation', 'in', self.mapped('model'))]).unlink()

        # delete ir_crons created by user
        crons = self.env['ir.cron'].with_context(active_test=False).search([('model_id', 'in', self.ids)])
        if crons:
            crons.unlink()

        self._drop_table()
        res = super(IrModel, self).unlink()

        # Reload registry for normal unlink only. For module uninstall, the
        # reload is done independently in odoo.modules.loading.
        if not self._context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this automatically removes model from registry
            self.env.flush_all()
            self.pool.setup_models(self._cr)

        return res

    def write(self, vals):
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
        res = super(IrModel, self).write(vals)
        # ordering has been changed, reload registry to reflect update + signaling
        if 'order' in vals:
            self.env.flush_all()  # setup_models need to fetch the updated values from the db
            self.pool.setup_models(self._cr)
        return res

    @api.model_create_multi
    def create(self, vals_list):
        res = super(IrModel, self).create(vals_list)
        manual_models = [
            vals['model'] for vals in vals_list if vals.get('state', 'manual') == 'manual'
        ]
        if manual_models:
            # setup models; this automatically adds model in registry
            self.env.flush_all()
            self.pool.setup_models(self._cr)
            # update database schema
            self.pool.init_models(self._cr, manual_models, dict(self._context, update_custom_fields=True))
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
            'order': model._order,
            'info': next(cls.__doc__ for cls in type(model).mro() if cls.__doc__),
            'state': 'manual' if model._custom else 'base',
            'transient': model._transient,
        }

    def _reflect_models(self, model_names):
        """ Reflect the given models. """
        # determine expected and existing rows
        rows = [
            self._reflect_model_params(self.env[model_name])
            for model_name in model_names
        ]
        cols = list(unique(['model'] + list(rows[0])))
        expected = [tuple(row[col] for col in cols) for row in rows]

        model_ids = {}
        existing = {}
        for row in select_en(self, ['id'] + cols, "model IN %s", [tuple(model_names)]):
            model_ids[row[1]] = row[0]
            existing[row[1]] = row[1:]

        # create or update rows
        rows = [row for row in expected if existing.get(row[0]) != row]
        if rows:
            ids = upsert_en(self, cols, rows, ['model'])
            for row, id_ in zip(rows, ids):
                model_ids[row[0]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[1:])

        # update their XML id
        module = self._context.get('module')
        if not module:
            return

        data_list = []
        for model_name, model_id in model_ids.items():
            model = self.env[model_name]
            if model._module == module:
                # model._module is the name of the module that last extended model
                xml_id = model_xmlid(module, model_name)
                record = self.browse(model_id)
                data_list.append({'xml_id': xml_id, 'record': record})
        self.env['ir.model.data']._update_xmlids(data_list)

    @api.model
    def _instanciate(self, model_data):
        """ Return a class for the custom model given by parameters ``model_data``. """
        class CustomModel(models.Model):
            _name = pycompat.to_text(model_data['model'])
            _description = model_data['name']
            _module = False
            _custom = True
            _transient = bool(model_data['transient'])
            _order = model_data['order']
            __doc__ = model_data['info']

        return CustomModel

    def _add_manual_models(self):
        """ Add extra models to the registry. """
        # clean up registry first
        for name, Model in list(self.pool.items()):
            if Model._custom:
                del self.pool.models[name]
                # remove the model's name from its parents' _inherit_children
                for Parent in Model.__bases__:
                    if hasattr(Parent, 'pool'):
                        Parent._inherit_children.discard(name)
        # add manual models
        cr = self.env.cr
        # we cannot use self._fields to determine translated fields, as it has not been set up yet
        cr.execute("SELECT *, name->>'en_US' AS name FROM ir_model WHERE state = 'manual'")
        for model_data in cr.dictfetchall():
            model_class = self._instanciate(model_data)
            Model = model_class._build_model(self.pool, cr)
            if tools.table_kind(cr, Model._table) not in ('r', None):
                # not a regular table, so disable schema upgrades
                Model._auto = False
                cr.execute(
                    '''
                    SELECT a.attname
                      FROM pg_attribute a
                      JOIN pg_class t
                        ON a.attrelid = t.oid
                       AND t.relname = %s
                     WHERE a.attnum > 0 -- skip system columns
                    ''',
                    [Model._table]
                )
                columns = {colinfo[0] for colinfo in cr.fetchall()}
                Model._log_access = set(models.LOG_ACCESS_COLUMNS) <= columns


# retrieve field types defined by the framework only (not extensions)
FIELD_TYPES = [(key, key) for key in sorted(fields.Field.by_type)]


class IrModelFields(models.Model):
    _name = 'ir.model.fields'
    _description = "Fields"
    _order = "name"
    _rec_name = 'field_description'

    name = fields.Char(string='Field Name', default='x_', required=True, index=True)
    complete_name = fields.Char(index=True)
    model = fields.Char(string='Model Name', required=True, index=True,
                        help="The technical name of the model this field belongs to")
    relation = fields.Char(string='Related Model',
                           help="For relationship fields, the technical name of the target model")
    relation_field = fields.Char(help="For one2many fields, the field on the target model that implement the opposite many2one relationship")
    relation_field_id = fields.Many2one('ir.model.fields', compute='_compute_relation_field_id',
                                        store=True, ondelete='cascade', string='Relation field')
    model_id = fields.Many2one('ir.model', string='Model', required=True, index=True, ondelete='cascade',
                               help="The model this field belongs to")
    field_description = fields.Char(string='Field Label', default='', required=True, translate=True)
    help = fields.Text(string='Field Help', translate=True)
    ttype = fields.Selection(selection=FIELD_TYPES, string='Field Type', required=True)
    selection = fields.Char(string="Selection Options (Deprecated)",
                            compute='_compute_selection', inverse='_inverse_selection')
    selection_ids = fields.One2many("ir.model.fields.selection", "field_id",
                                    string="Selection Options", copy=True)
    copied = fields.Boolean(string='Copied',
                            compute='_compute_copied', store=True, readonly=False,
                            help="Whether the value is copied when duplicating a record.")
    related = fields.Char(string='Related Field', help="The corresponding related field, if any. This must be a dot-separated list of field names.")
    related_field_id = fields.Many2one('ir.model.fields', compute='_compute_related_field_id',
                                       store=True, string="Related field", ondelete='cascade')
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
    groups = fields.Many2many('res.groups', 'ir_model_fields_group_rel', 'field_id', 'group_id') # CLEANME unimplemented field (empty table)
    group_expand = fields.Boolean(string="Expand Groups",
                                  help="If checked, all the records of the target model will be included\n"
                                        "in a grouped result (e.g. 'Group By' filters, Kanban columns, etc.).\n"
                                        "Note that it can significantly reduce performance if the target model\n"
                                        "of the field contains a lot of records; usually used on models with\n"
                                        "few records (e.g. Stages, Job Positions, Event Types, etc.).")
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

    @api.depends('relation', 'relation_field')
    def _compute_relation_field_id(self):
        for rec in self:
            if rec.state == 'manual' and rec.relation_field:
                rec.relation_field_id = self._get(rec.relation, rec.relation_field)
            else:
                rec.relation_field_id = False

    @api.depends('related')
    def _compute_related_field_id(self):
        for rec in self:
            if rec.state == 'manual' and rec.related:
                rec.related_field_id = rec._related_field()
            else:
                rec.related_field_id = False

    @api.depends('selection_ids')
    def _compute_selection(self):
        for rec in self:
            if rec.ttype in ('selection', 'reference'):
                rec.selection = str(self.env['ir.model.fields.selection']._get_selection(rec.id))
            else:
                rec.selection = False

    def _inverse_selection(self):
        for rec in self:
            selection = literal_eval(rec.selection or "[]")
            self.env['ir.model.fields.selection']._update_selection(rec.model, rec.name, selection)

    @api.depends('ttype', 'related', 'compute')
    def _compute_copied(self):
        for rec in self:
            rec.copied = (rec.ttype != 'one2many') and not (rec.related or rec.compute)

    @api.depends()
    def _in_modules(self):
        installed_modules = self.env['ir.module.module'].search([('state', '=', 'installed')])
        installed_names = set(installed_modules.mapped('name'))
        xml_ids = models.Model._get_external_ids(self)
        for field in self:
            module_names = set(xml_id.split('.')[0] for xml_id in xml_ids[field.id])
            field.modules = ", ".join(sorted(installed_names & module_names))

    @api.constrains('domain')
    def _check_domain(self):
        for field in self:
            safe_eval(field.domain or '[]')

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
        """ Return the ``ir.model.fields`` record corresponding to ``self.related``. """
        names = self.related.split(".")
        last = len(names) - 1
        model_name = self.model
        for index, name in enumerate(names):
            field = self._get(model_name, name)
            if not field:
                raise UserError(_("Unknown field name '%s' in related field '%s'") % (name, self.related))
            model_name = field.relation
            if index < last and not field.relation:
                raise UserError(_("Non-relational field name '%s' in related field '%s'") % (name, self.related))
        return field

    @api.constrains('related')
    def _check_related(self):
        for rec in self:
            if rec.state == 'manual' and rec.related:
                field = rec._related_field()
                if field.ttype != rec.ttype:
                    raise ValidationError(_("Related field '%s' does not have type '%s'") % (rec.related, rec.ttype))
                if field.relation != rec.relation:
                    raise ValidationError(_("Related field '%s' does not have comodel '%s'") % (rec.related, rec.relation))

    @api.onchange('related')
    def _onchange_related(self):
        if self.related:
            try:
                field = self._related_field()
            except UserError as e:
                return {'warning': {'title': _("Warning"), 'message': e}}
            self.ttype = field.ttype
            self.relation = field.relation
            self.readonly = True

    @api.onchange('relation')
    def _onchange_relation(self):
        try:
            self._check_relation()
        except ValidationError as e:
            return {'warning': {'title': _("Model %s does not exist", self.relation), 'message': e}}

    @api.constrains('relation')
    def _check_relation(self):
        for rec in self:
            if rec.state == 'manual' and rec.relation and not rec.env['ir.model']._get_id(rec.relation):
                raise ValidationError(_("Unknown model name '%s' in Related Model", rec.relation))

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
                    if name == 'id':
                        raise UserError(_("Compute method cannot depend on field 'id'"))
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

    @api.constrains('relation_table')
    def _check_relation_table(self):
        for rec in self:
            if rec.relation_table:
                models.check_pg_name(rec.relation_table)

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
        if self.ttype == 'many2many' and self.model_id and self.relation:
            if self.relation not in self.env:
                return
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
                                  ('id', 'not in', self.ids)])
            if others:
                for other in others:
                    if (other.model, other.relation) == (self.relation, self.model):
                        # other is a candidate inverse field
                        self.column1 = other.column2
                        self.column2 = other.column1
                        return
                return {'warning': {
                    'title': _("Warning"),
                    'message': _("The table %r if used for other, possibly incompatible fields.", self.relation_table),
                }}

    @api.onchange('required', 'ttype', 'on_delete')
    def _onchange_required(self):
        for rec in self:
            if rec.ttype == 'many2one' and rec.required and rec.on_delete == 'set null':
                return {'warning': {'title': _("Warning"), 'message': _(
                    "The m2o field %s is required but declares its ondelete policy "
                    "as being 'set null'. Only 'restrict' and 'cascade' make sense.", rec.name,
                )}}

    def _get(self, model_name, name):
        """ Return the (sudoed) `ir.model.fields` record with the given model and name.
        The result may be an empty recordset if the model is not found.
        """
        field_id = model_name and name and self._get_ids(model_name).get(name)
        return self.sudo().browse(field_id)

    @tools.ormcache('model_name')
    def _get_ids(self, model_name):
        cr = self.env.cr
        cr.execute("SELECT name, id FROM ir_model_fields WHERE model=%s", [model_name])
        return dict(cr.fetchall())

    def _drop_column(self):
        tables_to_drop = set()

        for field in self:
            if field.name in models.MAGIC_COLUMNS:
                continue
            model = self.env.get(field.model)
            is_model = model is not None
            if field.store:
                # TODO: Refactor this brol in master
                if is_model and tools.column_exists(self._cr, model._table, field.name) and \
                        tools.table_kind(self._cr, model._table) == 'r':
                    self._cr.execute(sql.SQL('ALTER TABLE {} DROP COLUMN {} CASCADE').format(
                        sql.Identifier(model._table), sql.Identifier(field.name),
                    ))
                if field.state == 'manual' and field.ttype == 'many2many':
                    rel_name = field.relation_table or (is_model and model._fields[field.name].relation)
                    tables_to_drop.add(rel_name)
            if field.state == 'manual' and is_model:
                model._pop_field(field.name)

        if tables_to_drop:
            # drop the relation tables that are not used by other fields
            self._cr.execute("""SELECT relation_table FROM ir_model_fields
                                WHERE relation_table IN %s AND id NOT IN %s""",
                             (tuple(tables_to_drop), tuple(self.ids)))
            tables_to_keep = set(row[0] for row in self._cr.fetchall())
            for rel_name in tables_to_drop - tables_to_keep:
                self._cr.execute(sql.SQL('DROP TABLE {}').format(sql.Identifier(rel_name)))

        return True

    def _prepare_update(self):
        """ Check whether the fields in ``self`` may be modified or removed.
            This method prevents the modification/deletion of many2one fields
            that have an inverse one2many, for instance.
        """
        failed_dependencies = []
        for rec in self:
            model = self.env.get(rec.model)
            if model is not None:
                if rec.name in model._fields:
                    field = model._fields[rec.name]
                else:
                    # field hasn't been loaded (yet?)
                    continue
                for dep in self.pool.get_dependent_fields(field):
                    if dep.manual:
                        failed_dependencies.append((field, dep))
                for inverse in model.pool.field_inverses[field]:
                    if inverse.manual and inverse.type == 'one2many':
                        failed_dependencies.append((field, inverse))

        uninstalling = self._context.get(MODULE_UNINSTALL_FLAG)
        if not uninstalling and failed_dependencies:
            msg = _("The field '%s' cannot be removed because the field '%s' depends on it.")
            raise UserError(msg % failed_dependencies[0])
        elif failed_dependencies:
            dependants = {rel[1] for rel in failed_dependencies}
            to_unlink = [self._get(field.model_name, field.name) for field in dependants]
            self.browse().union(*to_unlink).unlink()

        self = self.filtered(lambda record: record.state == 'manual')
        if not self:
            return

        # remove pending write of this field
        # DLE P16: if there are pending updates of the field we currently try to unlink, pop them out from the cache
        # test `test_unlink_with_dependant`
        for record in self:
            model = self.env.get(record.model)
            field = model and model._fields.get(record.name)
            if field:
                self.env.cache.clear_dirty_field(field)
        # remove fields from registry, and check that views are not broken
        fields = [self.env[record.model]._pop_field(record.name) for record in self]
        domain = expression.OR([('arch_db', 'like', record.name)] for record in self)
        views = self.env['ir.ui.view'].search(domain)
        try:
            for view in views:
                view._check_xml()
        except Exception:
            if not uninstalling:
                raise UserError("\n".join([
                    _("Cannot rename/delete fields that are still present in views:"),
                    _("Fields: %s") % ", ".join(str(f) for f in fields),
                    _("View: %s", view.name),
                ]))
            else:
                # uninstall mode
                _logger.warning("The following fields were force-deleted to prevent a registry crash "
                        + ", ".join(str(f) for f in fields)
                        + " the following view might be broken %s" % view.name)
        finally:
            if not uninstalling:
                # the registry has been modified, restore it
                self.pool.setup_models(self._cr)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_manual(self):
        # Prevent manual deletion of module columns
        if any(field.state != 'manual' for field in self):
            raise UserError(_("This column contains module data and cannot be removed!"))

    def unlink(self):
        if not self:
            return True

        # prevent screwing up fields that depend on these fields
        self._prepare_update()

        # determine registry fields corresponding to self
        fields = OrderedSet()
        for record in self:
            try:
                fields.add(self.pool[record.model]._fields[record.name])
            except KeyError:
                pass

        # clean the registry from the fields to remove
        self.pool.registry_invalidated = True
        self.pool._discard_fields(fields)

        # discard the removed fields from fields to compute
        for field in fields:
            self.env.all.tocompute.pop(field, None)

        model_names = self.mapped('model')
        self._drop_column()
        res = super(IrModelFields, self).unlink()

        # The field we just deleted might be inherited, and the registry is
        # inconsistent in this case; therefore we reload the registry.
        if not self._context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this re-initializes models in registry
            self.env.flush_all()
            self.pool.setup_models(self._cr)
            # update database schema of model and its descendant models
            models = self.pool.descendants(model_names, '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

        return res

    @api.model_create_multi
    def create(self, vals_list):
        IrModel = self.env['ir.model']
        models = set()
        for vals in vals_list:
            if 'model_id' in vals:
                vals['model'] = IrModel.browse(vals['model_id']).model
            assert vals.get('model'), f"missing model name for {vals}"
            models.add(vals['model'])

        # for self._get_ids() in _update_selection()
        self.clear_caches()

        res = super(IrModelFields, self).create(vals_list)

        for vals in vals_list:
            if vals.get('state', 'manual') == 'manual':
                relation = vals.get('relation')
                if relation and not IrModel._get_id(relation):
                    raise UserError(_("Model %s does not exist!", vals['relation']))

                if vals.get('ttype') == 'one2many' and not self.search_count([
                    ('ttype', '=', 'many2one'),
                    ('model', '=', vals['relation']),
                    ('name', '=', vals['relation_field']),
                ]):
                    raise UserError(_("Many2one %s on model %s does not exist!") % (vals['relation_field'], vals['relation']))

        if any(model in self.pool for model in models):
            # setup models; this re-initializes model in registry
            self.env.flush_all()
            self.pool.setup_models(self._cr)
            # update database schema of models and their descendants
            models = self.pool.descendants(models, '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

        return res

    def write(self, vals):
        # if set, *one* column can be renamed here
        column_rename = None

        # names of the models to patch
        patched_models = set()
        if vals and self:
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
                    # We need to rename the field
                    item._prepare_update()
                    if item.ttype in ('one2many', 'many2many', 'binary'):
                        # those field names are not explicit in the database!
                        pass
                    else:
                        if column_rename:
                            raise UserError(_('Can only rename one field at a time!'))
                        column_rename = (obj._table, item.name, vals['name'], item.index, item.store)

                # We don't check the 'state', because it might come from the context
                # (thus be set for multiple fields) and will be ignored anyway.
                if obj is not None and field is not None:
                    patched_models.add(obj._name)

        # These shall never be written (modified)
        for column_name in ('model_id', 'model', 'state'):
            if column_name in vals:
                del vals[column_name]

        res = super(IrModelFields, self).write(vals)

        self.env.flush_all()

        if column_rename:
            # rename column in database, and its corresponding index if present
            table, oldname, newname, index, stored = column_rename
            if stored:
                self._cr.execute(
                    sql.SQL('ALTER TABLE {} RENAME COLUMN {} TO {}').format(
                        sql.Identifier(table),
                        sql.Identifier(oldname),
                        sql.Identifier(newname)
                    ))
                if index:
                    self._cr.execute(
                        sql.SQL('ALTER INDEX {} RENAME TO {}').format(
                            sql.Identifier(f'{table}_{oldname}_index'),
                            sql.Identifier(f'{table}_{newname}_index'),
                        ))

        if column_rename or patched_models:
            # setup models, this will reload all manual fields in registry
            self.env.flush_all()
            self.pool.setup_models(self._cr)

        if patched_models:
            # update the database schema of the models to patch
            models = self.pool.descendants(patched_models, '_inherits')
            self.pool.init_models(self._cr, models, dict(self._context, update_custom_fields=True))

        return res

    def update_field_translations(self, field_name, translations):
        res = super().update_field_translations(field_name, translations)
        if res:
            self.clear_caches()
        return res

    def name_get(self):
        res = []
        for field in self:
            res.append((field.id, '%s (%s)' % (field.field_description, field.model)))
        return res

    def _reflect_field_params(self, field, model_id):
        """ Return the values to write to the database for the given field. """
        return {
            'model_id': model_id,
            'model': field.model_name,
            'name': field.name,
            'field_description': field.string,
            'help': field.help or None,
            'ttype': field.type,
            'state': 'manual' if field.manual else 'base',
            'relation': field.comodel_name or None,
            'index': bool(field.index),
            'store': bool(field.store),
            'copied': bool(field.copy),
            'on_delete': field.ondelete if field.type == 'many2one' else None,
            'related': field.related or None,
            'readonly': bool(field.readonly),
            'required': bool(field.required),
            'selectable': bool(field.search or field.store),
            'size': getattr(field, 'size', None),
            'translate': bool(field.translate),
            'relation_field': field.inverse_name if field.type == 'one2many' else None,
            'relation_table': field.relation if field.type == 'many2many' else None,
            'column1': field.column1 if field.type == 'many2many' else None,
            'column2': field.column2 if field.type == 'many2many' else None,
        }

    def _reflect_fields(self, model_names):
        """ Reflect the fields of the given models. """
        cr = self.env.cr

        for model_name in model_names:
            model = self.env[model_name]
            by_label = {}
            for field in model._fields.values():
                if field.string in by_label:
                    other = by_label[field.string]
                    _logger.warning('Two fields (%s, %s) of %s have the same label: %s. [Modules: %s and %s]',
                                    field.name, other.name, model, field.string, field._module, other._module)
                else:
                    by_label[field.string] = field

        # determine expected and existing rows
        rows = []
        for model_name in model_names:
            model_id = self.env['ir.model']._get_id(model_name)
            for field in self.env[model_name]._fields.values():
                rows.append(self._reflect_field_params(field, model_id))
        if not rows:
            return
        cols = list(unique(['model', 'name'] + list(rows[0])))
        expected = [tuple(row[col] for col in cols) for row in rows]

        field_ids = {}
        existing = {}
        for row in select_en(self, ['id'] + cols, "model IN %s", [tuple(model_names)]):
            field_ids[row[1:3]] = row[0]
            existing[row[1:3]] = row[1:]

        # create or update rows
        rows = [row for row in expected if existing.get(row[:2]) != row]
        if rows:
            ids = upsert_en(self, cols, rows, ['model', 'name'])
            for row, id_ in zip(rows, ids):
                field_ids[row[:2]] = id_
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        # update their XML id
        module = self._context.get('module')
        if not module:
            return

        data_list = []
        for (field_model, field_name), field_id in field_ids.items():
            model = self.env[field_model]
            field = model._fields.get(field_name)
            if field and (
                module == model._original_module
                or module in field._modules
                or any(
                    # module introduced field on model by inheritance
                    field_name in self.env[parent]._fields
                    for parent, parent_module in model._inherit_module.items()
                    if module == parent_module
                )
            ):
                xml_id = field_xmlid(module, field_model, field_name)
                record = self.browse(field_id)
                data_list.append({'xml_id': xml_id, 'record': record})
        self.env['ir.model.data']._update_xmlids(data_list)

    @tools.ormcache()
    def _all_manual_field_data(self):
        cr = self._cr
        # we cannot use self._fields to determine translated fields, as it has not been set up yet
        cr.execute("""
            SELECT *, field_description->>'en_US' AS field_description, help->>'en_US' AS help
            FROM ir_model_fields
            WHERE state = 'manual'
        """)
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
            'copy': bool(field_data['copied']),
            'related': field_data['related'],
            'required': bool(field_data['required']),
            'readonly': bool(field_data['readonly']),
            'store': bool(field_data['store']),
        }
        if field_data['ttype'] in ('char', 'text', 'html'):
            attrs['translate'] = bool(field_data['translate'])
            if field_data['ttype'] == 'char':
                attrs['size'] = field_data['size'] or None
        elif field_data['ttype'] in ('selection', 'reference'):
            attrs['selection'] = self.env['ir.model.fields.selection']._get_selection_data(field_data['id'])
            if field_data['ttype'] == 'selection':
                attrs['group_expand'] = field_data['group_expand']
        elif field_data['ttype'] == 'many2one':
            if not self.pool.loaded and field_data['relation'] not in self.env:
                return
            attrs['comodel_name'] = field_data['relation']
            attrs['ondelete'] = field_data['on_delete']
            attrs['domain'] = safe_eval(field_data['domain'] or '[]')
            attrs['group_expand'] = '_read_group_expand_full' if field_data['group_expand'] else None
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
                try:
                    field = self._instanciate(field_data)
                    if field:
                        model._add_field(name, field)
                except Exception:
                    _logger.exception("Failed to load field %s.%s: skipped", model._name, field_data['name'])

    @api.model
    @tools.ormcache_context('model_name', keys=('lang',))
    def get_field_string(self, model_name):
        """ Return the translation of fields strings in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' strings as a dictionary `{field_name: field_string}`
        """
        fields = self.sudo().search([('model', '=', model_name)])
        return {field.name: field.field_description for field in fields}

    @api.model
    @tools.ormcache_context('model_name', keys=('lang',))
    def get_field_help(self, model_name):
        """ Return the translation of fields help in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of a model
        :return: the model's fields' help as a dictionary `{field_name: field_help}`
        """
        fields = self.sudo().search([('model', '=', model_name)])
        return {field.name: field.help for field in fields}

    @api.model
    @tools.ormcache_context('model_name', 'field_name', keys=('lang',))
    def get_field_selection(self, model_name, field_name):
        """ Return the translation of a field's selection in the context's language.
        Note that the result contains the available translations only.

        :param model_name: the name of the field's model
        :param field_name: the name of the field
        :return: the fields' selection as a list
        """
        field = self._get(model_name, field_name)
        return [(sel.value, sel.name) for sel in field.selection_ids]

class IrModelSelection(models.Model):
    _name = 'ir.model.fields.selection'
    _order = 'sequence, id'
    _description = "Fields Selection"

    field_id = fields.Many2one("ir.model.fields",
        required=True, ondelete="cascade", index=True,
        domain=[('ttype', 'in', ['selection', 'reference'])])
    value = fields.Char(required=True)
    name = fields.Char(translate=True, required=True)
    sequence = fields.Integer(default=1000)

    _sql_constraints = [
        ('selection_field_uniq', 'unique(field_id, value)',
         'Selections values must be unique per field'),
    ]

    def _get_selection(self, field_id):
        """ Return the given field's selection as a list of pairs (value, string). """
        self.flush_model(['value', 'name', 'field_id', 'sequence'])
        return self._get_selection_data(field_id)

    def _get_selection_data(self, field_id):
        # return selection as expected on registry (no translations)
        self._cr.execute("""
            SELECT value, name->>'en_US'
            FROM ir_model_fields_selection
            WHERE field_id=%s
            ORDER BY sequence, id
        """, (field_id,))
        return self._cr.fetchall()

    def _reflect_selections(self, model_names):
        """ Reflect the selections of the fields of the given models. """
        fields = [
            field
            for model_name in model_names
            for field_name, field in self.env[model_name]._fields.items()
            if field.type in ('selection', 'reference')
            if isinstance(field.selection, list)
        ]
        if not fields:
            return

        # determine expected and existing rows
        IMF = self.env['ir.model.fields']
        expected = {
            (field_id, value): (label, index)
            for field in fields
            for field_id in [IMF._get_ids(field.model_name)[field.name]]
            for index, (value, label) in enumerate(field.selection)
        }

        cr = self.env.cr
        query = """
            SELECT s.field_id, s.value, s.name->>'en_US', s.sequence
            FROM ir_model_fields_selection s, ir_model_fields f
            WHERE s.field_id = f.id AND f.model IN %s
        """
        cr.execute(query, [tuple(model_names)])
        existing = {row[:2]: row[2:] for row in cr.fetchall()}

        # create or update rows
        cols = ['field_id', 'value', 'name', 'sequence']
        rows = [key + val for key, val in expected.items() if existing.get(key) != val]
        if rows:
            ids = upsert_en(self, cols, rows, ['field_id', 'value'])
            self.pool.post_init(mark_modified, self.browse(ids), cols[2:])

        # update their XML ids
        module = self._context.get('module')
        if not module:
            return

        query = """
            SELECT f.model, f.name, s.value, s.id
            FROM ir_model_fields_selection s, ir_model_fields f
            WHERE s.field_id = f.id AND f.model IN %s
        """
        cr.execute(query, [tuple(model_names)])
        selection_ids = {row[:3]: row[3] for row in cr.fetchall()}

        data_list = []
        for field in fields:
            model = self.env[field.model_name]
            for value, modules in field._selection_modules(model).items():
                for m in modules:
                    xml_id = selection_xmlid(m, field.model_name, field.name, value)
                    record = self.browse(selection_ids[field.model_name, field.name, value])
                    data_list.append({'xml_id': xml_id, 'record': record})
        self.env['ir.model.data']._update_xmlids(data_list)

    def _update_selection(self, model_name, field_name, selection):
        """ Set the selection of a field to the given list, and return the row
            values of the given selection records.
        """
        field_id = self.env['ir.model.fields']._get_ids(model_name)[field_name]

        # selection rows {value: row}
        cur_rows = self._existing_selection_data(model_name, field_name)
        new_rows = {
            value: dict(value=value, name=label, sequence=index)
            for index, (value, label) in enumerate(selection)
        }

        rows_to_insert = []
        rows_to_update = []
        rows_to_remove = []
        for value in new_rows.keys() | cur_rows.keys():
            new_row, cur_row = new_rows.get(value), cur_rows.get(value)
            if new_row is None:
                if self.pool.ready:
                    # removing a selection in the new list, at your own risks
                    _logger.warning("Removing selection value %s on %s.%s",
                                    cur_row['value'], model_name, field_name)
                    rows_to_remove.append(cur_row['id'])
            elif cur_row is None:
                new_row['name'] = Json({'en_US': new_row['name']})
                rows_to_insert.append(dict(new_row, field_id=field_id))
            elif any(new_row[key] != cur_row[key] for key in new_row):
                new_row['name'] = Json({'en_US': new_row['name']})
                rows_to_update.append(dict(new_row, id=cur_row['id']))

        if rows_to_insert:
            row_ids = query_insert(self.env.cr, self._table, rows_to_insert)
            # update cur_rows for output
            for row, row_id in zip(rows_to_insert, row_ids):
                cur_rows[row['value']] = dict(row, id=row_id)

        for row in rows_to_update:
            query_update(self.env.cr, self._table, row, ['id'])

        if rows_to_remove:
            self.browse(rows_to_remove).unlink()

        return cur_rows

    def _existing_selection_data(self, model_name, field_name):
        """ Return the selection data of the given model, by field and value, as
            a dict {field_name: {value: row_values}}.
        """
        query = """
            SELECT s.*, s.name->>'en_US' AS name
            FROM ir_model_fields_selection s
            JOIN ir_model_fields f ON s.field_id=f.id
            WHERE f.model=%s and f.name=%s
        """
        self._cr.execute(query, [model_name, field_name])
        return {row['value']: row for row in self._cr.dictfetchall()}

    @api.model_create_multi
    def create(self, vals_list):
        field_ids = {vals['field_id'] for vals in vals_list}
        field_names = set()
        for field in self.env['ir.model.fields'].browse(field_ids):
            field_names.add((field.model, field.name))
            if field.state != 'manual':
                raise UserError(_('Properties of base fields cannot be altered in this manner! '
                                  'Please modify them through Python code, '
                                  'preferably through a custom addon!'))
        recs = super().create(vals_list)

        if any(
            model in self.pool and name in self.pool[model]._fields
            for model, name in field_names
        ):
            # setup models; this re-initializes model in registry
            self.env.flush_all()
            self.pool.setup_models(self._cr)

        return recs

    def write(self, vals):
        if (
            not self.env.user._is_admin() and
            any(record.field_id.state != 'manual' for record in self)
        ):
            raise UserError(_('Properties of base fields cannot be altered in this manner! '
                              'Please modify them through Python code, '
                              'preferably through a custom addon!'))

        if 'value' in vals:
            for selection in self:
                if selection.value == vals['value']:
                    continue
                if selection.field_id.store:
                    # in order to keep the cache consistent, flush the
                    # corresponding field, and invalidate it from cache
                    model = self.env[selection.field_id.model]
                    fname = selection.field_id.name
                    model.invalidate_model([fname])
                    # replace the value by the new one in the field's corresponding column
                    query = f'UPDATE "{model._table}" SET "{fname}"=%s WHERE "{fname}"=%s'
                    self.env.cr.execute(query, [vals['value'], selection.value])

        result = super().write(vals)

        # setup models; this re-initializes model in registry
        self.env.flush_all()
        self.pool.setup_models(self._cr)

        return result

    @api.ondelete(at_uninstall=False)
    def _unlink_if_manual(self):
        # Prevent manual deletion of module columns
        if (
            self.pool.ready
            and any(selection.field_id.state != 'manual' for selection in self)
        ):
            raise UserError(_('Properties of base fields cannot be altered in this manner! '
                              'Please modify them through Python code, '
                              'preferably through a custom addon!'))

    def unlink(self):
        self._process_ondelete()
        result = super().unlink()

        # Reload registry for normal unlink only. For module uninstall, the
        # reload is done independently in odoo.modules.loading.
        if not self._context.get(MODULE_UNINSTALL_FLAG):
            # setup models; this re-initializes model in registry
            self.env.flush_all()
            self.pool.setup_models(self._cr)

        return result

    def _process_ondelete(self):
        """ Process the 'ondelete' of the given selection values. """
        def safe_write(records, fname, value):
            if not records:
                return
            try:
                with self.env.cr.savepoint():
                    records.write({fname: value})
            except Exception:
                # going through the ORM failed, probably because of an exception
                # in an override or possibly a constraint.
                _logger.runbot(
                    "Could not fulfill ondelete action for field %s.%s, "
                    "attempting ORM bypass...", records._name, fname,
                )
                query = sql.SQL("UPDATE {} SET {}=%s WHERE id IN %s").format(
                    sql.Identifier(records._table),
                    sql.Identifier(fname),
                )
                # if this fails then we're shit out of luck and there's nothing
                # we can do except fix on a case-by-case basis
                value = field.convert_to_column(value, records)
                self.env.cr.execute(query, [value, records._ids])
                records.invalidate_recordset([fname])

        for selection in self:
            Model = self.env[selection.field_id.model]
            # The field may exist in database but not in registry. In this case
            # we allow the field to be skipped, but for production this should
            # be handled through a migration script. The ORM will take care of
            # the orphaned 'ir.model.fields' down the stack, and will log a
            # warning prompting the developer to write a migration script.
            field = Model._fields.get(selection.field_id.name)
            if not field or not field.store or Model._abstract:
                continue

            ondelete = (field.ondelete or {}).get(selection.value)
            # special case for custom fields
            if ondelete is None and field.manual and not field.required:
                ondelete = 'set null'

            if ondelete is None:
                # nothing to do, the selection does not come from a field extension
                continue
            elif callable(ondelete):
                ondelete(selection._get_records())
            elif ondelete == 'set null':
                safe_write(selection._get_records(), field.name, False)
            elif ondelete == 'set default':
                value = field.convert_to_write(field.default(Model), Model)
                safe_write(selection._get_records(), field.name, value)
            elif ondelete.startswith('set '):
                safe_write(selection._get_records(), field.name, ondelete[4:])
            elif ondelete == 'cascade':
                selection._get_records().unlink()
            else:
                # this shouldn't happen... simply a sanity check
                raise ValueError(_(
                    "The ondelete policy %r is not valid for field %r"
                ) % (ondelete, selection))

    def _get_records(self):
        """ Return the records having 'self' as a value. """
        self.ensure_one()
        Model = self.env[self.field_id.model]
        Model.flush_model([self.field_id.name])
        query = 'SELECT id FROM "{table}" WHERE "{field}"=%s'.format(
            table=Model._table, field=self.field_id.name,
        )
        self.env.cr.execute(query, [self.value])
        return Model.browse(r[0] for r in self.env.cr.fetchall())


class IrModelConstraint(models.Model):
    """
    This model tracks PostgreSQL foreign keys and constraints used by Odoo
    models.
    """
    _name = 'ir.model.constraint'
    _description = 'Model Constraint'

    name = fields.Char(string='Constraint', required=True, index=True,
                       help="PostgreSQL constraint or foreign key name.")
    definition = fields.Char(help="PostgreSQL constraint definition")
    message = fields.Char(help="Error message returned when the constraint is violated.", translate=True)
    model = fields.Many2one('ir.model', required=True, ondelete="cascade", index=True)
    module = fields.Many2one('ir.module.module', required=True, index=True, ondelete='cascade')
    type = fields.Char(string='Constraint Type', required=True, size=1, index=True,
                       help="Type of the constraint: `f` for a foreign key, "
                            "`u` for other constraints.")
    write_date = fields.Datetime()
    create_date = fields.Datetime()

    _sql_constraints = [
        ('module_name_uniq', 'unique(name, module)',
         'Constraints with the same name are unique per module.'),
    ]

    def _module_data_uninstall(self):
        """
        Delete PostgreSQL foreign keys and constraints tracked by this model.
        """
        if not self.env.is_system():
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
                    self._cr.execute(
                        sql.SQL('ALTER TABLE {} DROP CONSTRAINT {}').format(
                            sql.Identifier(table),
                            sql.Identifier(name[:63])
                        ))
                    _logger.info('Dropped FK CONSTRAINT %s@%s', name, data.model.model)

            if typ == 'u':
                # test if constraint exists
                # Since type='u' means any "other" constraint, to avoid issues we limit to
                # 'c' -> check, 'u' -> unique, 'x' -> exclude constraints, effective leaving
                # out 'p' -> primary key and 'f' -> foreign key, constraints.
                # See: https://www.postgresql.org/docs/9.5/catalog-pg-constraint.html
                self._cr.execute("""SELECT 1 from pg_constraint cs JOIN pg_class cl ON (cs.conrelid = cl.oid)
                                    WHERE cs.contype in ('c', 'u', 'x') and cs.conname=%s and cl.relname=%s""",
                                 (name[:63], table))
                if self._cr.fetchone():
                    self._cr.execute(sql.SQL('ALTER TABLE {} DROP CONSTRAINT {}').format(
                        sql.Identifier(table), sql.Identifier(name[:63])))
                    _logger.info('Dropped CONSTRAINT %s@%s', name, data.model.model)

        self.unlink()

    def copy(self, default=None):
        default = dict(default or {})
        default['name'] = self.name + '_copy'
        return super(IrModelConstraint, self).copy(default)

    def _reflect_constraint(self, model, conname, type, definition, module, message=None):
        """ Reflect the given constraint, and return its corresponding record.
            The reflection makes it possible to remove a constraint when its
            corresponding module is uninstalled. ``type`` is either 'f' or 'u'
            depending on the constraint being a foreign key or not.
        """
        if not module:
            # no need to save constraints for custom models as they're not part
            # of any module
            return
        assert type in ('f', 'u')
        cr = self._cr
        query = """ SELECT c.id, type, definition, message->>'en_US' as message
                    FROM ir_model_constraint c, ir_module_module m
                    WHERE c.module=m.id AND c.name=%s AND m.name=%s """
        cr.execute(query, (conname, module))
        cons = cr.dictfetchone()
        if not cons:
            query = """ INSERT INTO ir_model_constraint
                            (name, create_date, write_date, create_uid, write_uid, module, model, type, definition, message)
                        VALUES (%s,
                                now() AT TIME ZONE 'UTC',
                                now() AT TIME ZONE 'UTC',
                                %s, %s,
                                (SELECT id FROM ir_module_module WHERE name=%s),
                                (SELECT id FROM ir_model WHERE model=%s),
                                %s, %s, %s)
                        RETURNING id"""
            cr.execute(query, (conname, self.env.uid, self.env.uid, module, model._name, type, definition, Json({'en_US': message})))
            return self.browse(cr.fetchone()[0])

        cons_id = cons.pop('id')
        if cons != dict(type=type, definition=definition, message=message):
            query = """ UPDATE ir_model_constraint
                        SET write_date=now() AT TIME ZONE 'UTC',
                            write_uid=%s, type=%s, definition=%s, message=%s
                        WHERE id=%s"""
            cr.execute(query, (self.env.uid, type, definition, Json({'en_US': message}), cons_id))
        return self.browse(cons_id)

    def _reflect_constraints(self, model_names):
        """ Reflect the SQL constraints of the given models. """
        for model_name in model_names:
            self._reflect_model(self.env[model_name])

    def _reflect_model(self, model):
        """ Reflect the _sql_constraints of the given model. """
        def cons_text(txt):
            return txt.lower().replace(', ',',').replace(' (','(')

        # map each constraint on the name of the module where it is defined
        constraint_module = {
            constraint[0]: cls._module
            for cls in reversed(type(model).mro())
            if models.is_definition_class(cls)
            for constraint in getattr(cls, '_local_sql_constraints', ())
        }

        data_list = []
        for (key, definition, message) in model._sql_constraints:
            conname = '%s_%s' % (model._table, key)
            module = constraint_module.get(key)
            record = self._reflect_constraint(model, conname, 'u', cons_text(definition), module, message)
            if record:
                xml_id = '%s.constraint_%s' % (module, conname)
                data_list.append(dict(xml_id=xml_id, record=record))

        self.env['ir.model.data']._update_xmlids(data_list)


class IrModelRelation(models.Model):
    """
    This model tracks PostgreSQL tables used to implement Odoo many2many
    relations.
    """
    _name = 'ir.model.relation'
    _description = 'Relation Model'

    name = fields.Char(string='Relation Name', required=True, index=True,
                       help="PostgreSQL table name implementing a many2many relation.")
    model = fields.Many2one('ir.model', required=True, index=True, ondelete='cascade')
    module = fields.Many2one('ir.module.module', required=True, index=True, ondelete='cascade')
    write_date = fields.Datetime()
    create_date = fields.Datetime()

    def _module_data_uninstall(self):
        """
        Delete PostgreSQL many2many relations tracked by this model.
        """
        if not self.env.is_system():
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
            self._cr.execute(sql.SQL('DROP TABLE {} CASCADE').format(sql.Identifier(table)))
            _logger.info('Dropped table %s', table)

    def _reflect_relation(self, model, table, module):
        """ Reflect the table of a many2many field for the given model, to make
            it possible to delete it later when the module is uninstalled.
        """
        self.env.invalidate_all()
        cr = self._cr
        query = """ SELECT 1 FROM ir_model_relation r, ir_module_module m
                    WHERE r.module=m.id AND r.name=%s AND m.name=%s """
        cr.execute(query, (table, module))
        if not cr.rowcount:
            query = """ INSERT INTO ir_model_relation
                            (name, create_date, write_date, create_uid, write_uid, module, model)
                        VALUES (%s,
                                now() AT TIME ZONE 'UTC',
                                now() AT TIME ZONE 'UTC',
                                %s, %s,
                                (SELECT id FROM ir_module_module WHERE name=%s),
                                (SELECT id FROM ir_model WHERE model=%s)) """
            cr.execute(query, (table, self.env.uid, self.env.uid, module, model._name))


class IrModelAccess(models.Model):
    _name = 'ir.model.access'
    _description = 'Model Access'
    _order = 'model_id,group_id,name,id'

    name = fields.Char(required=True, index=True)
    active = fields.Boolean(default=True, help='If you uncheck the active field, it will disable the ACL without deleting it (if you delete a native ACL, it will be re-created when you reload the module).')
    model_id = fields.Many2one('ir.model', string='Model', required=True, index=True, ondelete='cascade')
    group_id = fields.Many2one('res.groups', string='Group', ondelete='restrict', index=True)
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

        if isinstance(group_ids, int):
            group_ids = [group_ids]

        query = """ SELECT 1 FROM ir_model_access a
                    JOIN ir_model m ON (m.id = a.model_id)
                    WHERE a.active AND a.perm_{mode} AND
                        m.model=%s AND (a.group_id IN %s OR a.group_id IS NULL)
                """.format(mode=mode)
        self._cr.execute(query, (model_name, tuple(group_ids)))
        return bool(self._cr.rowcount)

    @api.model
    def group_names_with_access(self, model_name, access_mode):
        """ Return the names of visible groups which have been granted
            ``access_mode`` on the model ``model_name``.
           :rtype: list
        """
        assert access_mode in ('read', 'write', 'create', 'unlink'), 'Invalid access mode'
        lang = self.env.lang or 'en_US'
        self._cr.execute(f"""
            SELECT COALESCE(c.name->>%s, c.name->>'en_US'), COALESCE(g.name->>%s, g.name->>'en_US')
              FROM ir_model_access a
              JOIN ir_model m ON (a.model_id = m.id)
              JOIN res_groups g ON (a.group_id = g.id)
         LEFT JOIN ir_module_category c ON (c.id = g.category_id)
             WHERE m.model = %s
               AND a.active = TRUE
               AND a.perm_{access_mode} = TRUE
          ORDER BY c.name, g.name NULLS LAST
        """, [lang, lang, model_name])
        return [('%s/%s' % x) if x[0] else x[1] for x in self._cr.fetchall()]

    # The context parameter is useful when the method translates error messages.
    # But as the method raises an exception in that case,  the key 'lang' might
    # not be really necessary as a cache key, unless the `ormcache_context`
    # decorator catches the exception (it does not at the moment.)

    @tools.ormcache('self.env.uid', 'mode')
    def _get_allowed_models(self, mode='read'):
        assert mode in ('read', 'write', 'create', 'unlink'), 'Invalid access mode'

        self.flush_model()
        self.env.cr.execute(f"""
            SELECT m.model
              FROM ir_model_access a
              JOIN ir_model m ON (m.id = a.model_id)
             WHERE a.perm_{mode}
               AND a.active
               AND (
                    a.group_id IS NULL OR
                    -- use subselect fo force a better query plan. See #99695 --
                    a.group_id IN (
                        SELECT gu.gid
                            FROM res_groups_users_rel gu
                            WHERE gu.uid = %s
                    )
                )
            GROUP BY m.model
        """, (self.env.uid,))

        return frozenset(v[0] for v in self.env.cr.fetchall())

    @api.model
    def check(self, model, mode='read', raise_exception=True):
        if self.env.su:
            # User root have all accesses
            return True

        assert isinstance(model, str), 'Not a model name: %s' % (model,)

        # TransientModel records have no access rights, only an implicit access rule
        if model not in self.env:
            _logger.error('Missing model %s', model)

        has_access = model in self._get_allowed_models(mode)

        if not has_access and raise_exception:
            groups = '\n'.join('\t- %s' % g for g in self.group_names_with_access(model, mode))
            document_kind = self.env['ir.model']._get(model).name or model
            msg_heads = {
                # Messages are declared in extenso so they are properly exported in translation terms
                'read': _lt(
                    "You are not allowed to access '%(document_kind)s' (%(document_model)s) records.",
                    document_kind=document_kind,
                    document_model=model,
                ),
                'write':  _lt(
                    "You are not allowed to modify '%(document_kind)s' (%(document_model)s) records.",
                    document_kind=document_kind,
                    document_model=model,
                ),
                'create': _lt(
                    "You are not allowed to create '%(document_kind)s' (%(document_model)s) records.",
                    document_kind=document_kind,
                    document_model=model,
                ),
                'unlink': _lt(
                    "You are not allowed to delete '%(document_kind)s' (%(document_model)s) records.",
                    document_kind=document_kind,
                    document_model=model,
                ),
            }
            operation_error = msg_heads[mode]

            if groups:
                group_info = _("This operation is allowed for the following groups:\n%(groups_list)s", groups_list=groups)
            else:
                group_info = _("No group currently allows this operation.")

            resolution_info = _("Contact your administrator to request access if necessary.")

            _logger.info('Access Denied by ACLs for operation: %s, uid: %s, model: %s', mode, self._uid, model)
            msg = """{operation_error}

{group_info}

{resolution_info}""".format(
                operation_error=operation_error,
                group_info=group_info,
                resolution_info=resolution_info)

            raise AccessError(msg)

        return has_access

    __cache_clearing_methods = set()

    @classmethod
    def register_cache_clearing_method(cls, model, method):
        cls.__cache_clearing_methods.add((model, method))

    @classmethod
    def unregister_cache_clearing_method(cls, model, method):
        cls.__cache_clearing_methods.discard((model, method))

    @api.model
    def call_cache_clearing_methods(self):
        self.env.invalidate_all()
        self._get_allowed_models.clear_cache(self)    # clear the cache of check function
        for model, method in self.__cache_clearing_methods:
            if model in self.env:
                getattr(self.env[model], method)()

    #
    # Check rights on actions
    #
    @api.model_create_multi
    def create(self, vals_list):
        self.call_cache_clearing_methods()
        return super(IrModelAccess, self).create(vals_list)

    def write(self, values):
        self.call_cache_clearing_methods()
        return super(IrModelAccess, self).write(values)

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
    _description = 'Model Data'
    _order = 'module, model, name'

    name = fields.Char(string='External Identifier', required=True,
                       help="External Key/Identifier that can be used for "
                            "data integration with third-party systems")
    complete_name = fields.Char(compute='_compute_complete_name', string='Complete ID')
    model = fields.Char(string='Model Name', required=True)
    module = fields.Char(default='', required=True)
    res_id = fields.Many2oneReference(string='Record ID', help="ID of the target record in the database", model_field='model')
    noupdate = fields.Boolean(string='Non Updatable', default=False)
    reference = fields.Char(string='Reference', compute='_compute_reference', readonly=True, store=False)

    _sql_constraints = [
        ('name_nospaces', "CHECK(name NOT LIKE '% %')",
         "External IDs cannot contain spaces"),
    ]

    @api.depends('module', 'name')
    def _compute_complete_name(self):
        for res in self:
            res.complete_name = ".".join(n for n in [res.module, res.name] if n)

    @api.depends('model', 'res_id')
    def _compute_reference(self):
        for res in self:
            res.reference = "%s,%s" % (res.model, res.res_id)

    def _auto_init(self):
        res = super(IrModelData, self)._auto_init()
        tools.create_unique_index(self._cr, 'ir_model_data_module_name_uniq_index',
                                  self._table, ['module', 'name'])
        tools.create_index(self._cr, 'ir_model_data_model_res_id_index',
                           self._table, ['model', 'res_id'])
        return res

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
    def _xmlid_lookup(self, xmlid):
        """Low level xmlid lookup
        Return (id, res_model, res_id) or raise ValueError if not found
        """
        module, name = xmlid.split('.', 1)
        query = "SELECT id, model, res_id FROM ir_model_data WHERE module=%s AND name=%s"
        self.env.cr.execute(query, [module, name])
        result = self.env.cr.fetchone()
        if not (result and result[2]):
            raise ValueError('External ID not found in the system: %s' % xmlid)
        return result

    @api.model
    def _xmlid_to_res_model_res_id(self, xmlid, raise_if_not_found=False):
        """ Return (res_model, res_id)"""
        try:
            return self._xmlid_lookup(xmlid)[1:3]
        except ValueError:
            if raise_if_not_found:
                raise
            return (False, False)

    @api.model
    def _xmlid_to_res_id(self, xmlid, raise_if_not_found=False):
        """ Returns res_id """
        return self._xmlid_to_res_model_res_id(xmlid, raise_if_not_found)[1]

    @api.model
    def check_object_reference(self, module, xml_id, raise_on_access_error=False):
        """Returns (model, res_id) corresponding to a given module and xml_id (cached), if and only if the user has the necessary access rights
        to see that object, otherwise raise a ValueError if raise_on_access_error is True or returns a tuple (model found, False)"""
        model, res_id = self._xmlid_lookup("%s.%s" % (module, xml_id))[1:3]
        #search on id found in result to check if current user has read access right
        if self.env[model].search([('id', '=', res_id)]):
            return model, res_id
        if raise_on_access_error:
            raise AccessError(_('Not enough access rights on the external ID:') + ' %s.%s' % (module, xml_id))
        return model, False

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        rand = "%04x" % random.getrandbits(16)
        default = dict(default or {}, name="%s_%s" % (self.name, rand))
        return super().copy(default)

    def unlink(self):
        """ Regular unlink method, but make sure to clear the caches. """
        self.clear_caches()
        return super(IrModelData, self).unlink()

    def _lookup_xmlids(self, xml_ids, model):
        """ Look up the given XML ids of the given model. """
        if not xml_ids:
            return []

        # group xml_ids by prefix
        bymodule = defaultdict(set)
        for xml_id in xml_ids:
            prefix, suffix = xml_id.split('.', 1)
            bymodule[prefix].add(suffix)

        # query xml_ids by prefix
        result = []
        cr = self.env.cr
        for prefix, suffixes in bymodule.items():
            query = """
                SELECT d.id, d.module, d.name, d.model, d.res_id, d.noupdate, r.id
                FROM ir_model_data d LEFT JOIN "{}" r on d.res_id=r.id
                WHERE d.module=%s AND d.name IN %s
            """.format(model._table)
            for subsuffixes in cr.split_for_in_conditions(suffixes):
                cr.execute(query, (prefix, subsuffixes))
                result.extend(cr.fetchall())

        return result

    @api.model
    def _update_xmlids(self, data_list, update=False):
        """ Create or update the given XML ids.

            :param data_list: list of dicts with keys `xml_id` (XMLID to
                assign), `noupdate` (flag on XMLID), `record` (target record).
            :param update: should be ``True`` when upgrading a module
        """
        if not data_list:
            return

        rows = tools.OrderedSet()
        for data in data_list:
            prefix, suffix = data['xml_id'].split('.', 1)
            record = data['record']
            noupdate = bool(data.get('noupdate'))
            rows.add((prefix, suffix, record._name, record.id, noupdate))

        for sub_rows in self.env.cr.split_for_in_conditions(rows):
            # insert rows or update them
            query = self._build_update_xmlids_query(sub_rows, update)
            try:
                self.env.cr.execute(query, [arg for row in sub_rows for arg in row])
            except Exception:
                _logger.error("Failed to insert ir_model_data\n%s", "\n".join(str(row) for row in sub_rows))
                raise

        # update loaded_xmlids
        self.pool.loaded_xmlids.update("%s.%s" % row[:2] for row in rows)

    # NOTE: this method is overriden in web_studio; if you need to make another
    #  override, make sure it is compatible with the one that is there.
    def _build_update_xmlids_query(self, sub_rows, update):
        rowf = "(%s, %s, %s, %s, %s)"
        return """
            INSERT INTO ir_model_data (module, name, model, res_id, noupdate)
            VALUES {rows}
            ON CONFLICT (module, name)
            DO UPDATE SET (model, res_id, write_date) =
                (EXCLUDED.model, EXCLUDED.res_id, now() at time zone 'UTC')
                {where}
        """.format(
            rows=", ".join([rowf] * len(sub_rows)),
            where="WHERE NOT ir_model_data.noupdate" if update else "",
        )

    @api.model
    def _load_xmlid(self, xml_id):
        """ Simply mark the given XML id as being loaded, and return the
            corresponding record.
        """
        record = self.env.ref(xml_id, raise_if_not_found=False)
        if record:
            self.pool.loaded_xmlids.add(xml_id)
        return record

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
        if not self.env.is_system():
            raise AccessError(_('Administrator access is required to uninstall a module'))

        # enable model/field deletion
        # we deactivate prefetching to not try to read a column that has been deleted
        self = self.with_context(**{MODULE_UNINSTALL_FLAG: True, 'prefetch_fields': False})

        # determine records to unlink
        records_items = []              # [(model, id)]
        model_ids = []
        field_ids = []
        selection_ids = []
        constraint_ids = []

        module_data = self.search([('module', 'in', modules_to_remove)], order='id DESC')
        for data in module_data:
            if data.model == 'ir.model':
                model_ids.append(data.res_id)
            elif data.model == 'ir.model.fields':
                field_ids.append(data.res_id)
            elif data.model == 'ir.model.fields.selection':
                selection_ids.append(data.res_id)
            elif data.model == 'ir.model.constraint':
                constraint_ids.append(data.res_id)
            else:
                records_items.append((data.model, data.res_id))

        # avoid prefetching fields that are going to be deleted: during uninstall, it is
        # possible to perform a recompute (via flush) after the database columns have been
        # deleted but before the new registry has been created, meaning the recompute will
        # be executed on a stale registry, and if some of the data for executing the compute
        # methods is not in cache it will be fetched, and fields that exist in the registry but not
        # in the database will be prefetched, this will of course fail and prevent the uninstall.
        for ir_field in self.env['ir.model.fields'].browse(field_ids):
            model = self.pool.get(ir_field.model)
            if model is not None:
                field = model._fields.get(ir_field.name)
                if field is not None:
                    field.prefetch = False

        # to collect external ids of records that cannot be deleted
        undeletable_ids = []

        def delete(records):
            # do not delete records that have other external ids (and thus do
            # not belong to the modules being installed)
            ref_data = self.search([
                ('model', '=', records._name),
                ('res_id', 'in', records.ids),
            ])
            records -= records.browse((ref_data - module_data).mapped('res_id'))
            if not records:
                return

            # special case for ir.model.fields
            if records._name == 'ir.model.fields':
                missing = records - records.exists()
                if missing:
                    # delete orphan external ids right now;
                    # an orphan ir.model.data can happen if the ir.model.field is deleted via
                    # an ONDELETE CASCADE, in which case we must verify that the records we're
                    # processing exist in the database otherwise a MissingError will be raised
                    orphans = ref_data.filtered(lambda r: r.res_id in missing._ids)
                    _logger.info('Deleting orphan ir_model_data %s', orphans)
                    orphans.unlink()
                    # /!\ this must go before any field accesses on `records`
                    records -= missing
                # do not remove LOG_ACCESS_COLUMNS unless _log_access is False
                # on the model
                records -= records.filtered(lambda f: f.name == 'id' or (
                    f.name in models.LOG_ACCESS_COLUMNS and
                    f.model in self.env and self.env[f.model]._log_access
                ))

            # now delete the records
            _logger.info('Deleting %s', records)
            try:
                with self._cr.savepoint():
                    records.unlink()
            except Exception:
                if len(records) <= 1:
                    undeletable_ids.extend(ref_data._ids)
                else:
                    # divide the batch in two, and recursively delete them
                    half_size = len(records) // 2
                    delete(records[:half_size])
                    delete(records[half_size:])

        # remove non-model records first, grouped by batches of the same model
        for model, items in itertools.groupby(unique(records_items), itemgetter(0)):
            delete(self.env[model].browse(item[1] for item in items))

        # Remove copied views. This must happen after removing all records from
        # the modules to remove, otherwise ondelete='restrict' may prevent the
        # deletion of some view. This must also happen before cleaning up the
        # database schema, otherwise some dependent fields may no longer exist
        # in database.
        modules = self.env['ir.module.module'].search([('name', 'in', modules_to_remove)])
        modules._remove_copied_views()

        # remove constraints
        constraints = self.env['ir.model.constraint'].search([('module', 'in', modules.ids)])
        constraints._module_data_uninstall()
        delete(self.env['ir.model.constraint'].browse(unique(constraint_ids)))

        # If we delete a selection field, and some of its values have ondelete='cascade',
        # we expect the records with that value to be deleted. If we delete the field first,
        # the column is dropped and the selection is gone, and thus the records above will not
        # be deleted.
        delete(self.env['ir.model.fields.selection'].browse(unique(selection_ids)).exists())
        delete(self.env['ir.model.fields'].browse(unique(field_ids)))
        relations = self.env['ir.model.relation'].search([('module', 'in', modules.ids)])
        relations._module_data_uninstall()

        # remove models
        delete(self.env['ir.model'].browse(unique(model_ids)))

        # log undeletable ids
        _logger.info("ir.model.data could not be deleted (%s)", undeletable_ids)

        # sort out which undeletable model data may have become deletable again because
        # of records being cascade-deleted or tables being dropped just above
        for data in self.browse(undeletable_ids).exists():
            record = self.env[data.model].browse(data.res_id)
            try:
                with self.env.cr.savepoint():
                    if record.exists():
                        # record exists therefore the data is still undeletable,
                        # remove it from module_data
                        module_data -= data
                        continue
            except psycopg2.ProgrammingError:
                # This most likely means that the record does not exist, since record.exists()
                # is rougly equivalent to `SELECT id FROM table WHERE id=record.id` and it may raise
                # a ProgrammingError because the table no longer exists (and so does the
                # record), also applies to ir.model.fields, constraints, etc.
                pass
        # remove remaining module data records
        module_data.unlink()

    @api.model
    def _process_end_unlink_record(self, record):
        record.unlink()

    @api.model
    def _process_end(self, modules):
        """ Clear records removed from updated module data.
        This method is called at the end of the module loading process.
        It is meant to removed records that are no longer present in the
        updated data. Such records are recognised as the one with an xml id
        and a module in ir_model_data and noupdate set to false, but not
        present in self.pool.loaded_xmlids.
        """
        if not modules or tools.config.get('import_partial'):
            return True

        bad_imd_ids = []
        self = self.with_context({MODULE_UNINSTALL_FLAG: True})
        loaded_xmlids = self.pool.loaded_xmlids

        query = """ SELECT id, module || '.' || name, model, res_id FROM ir_model_data
                    WHERE module IN %s AND res_id IS NOT NULL AND COALESCE(noupdate, false) != %s ORDER BY id DESC
                """
        self._cr.execute(query, (tuple(modules), True))
        for (id, xmlid, model, res_id) in self._cr.fetchall():
            if xmlid in loaded_xmlids:
                continue

            Model = self.env.get(model)
            if Model is None:
                continue

            # when _inherits parents are implicitly created we give them an
            # external id (if their descendant has one) in order to e.g.
            # properly remove them when the module is deleted, however this
            # generated id is *not* provided during update yet we don't want to
            # try and remove either the xid or the record, so check if the
            # record has a child we've just updated
            keep = False
            for inheriting in (self.env[m] for m in Model._inherits_children):
                # ignore mixins
                if inheriting._abstract:
                    continue

                parent_field = inheriting._inherits[model]
                children = inheriting.with_context(active_test=False).search([(parent_field, '=', res_id)])
                children_xids = {
                    xid
                    for xids in (children and children._get_external_ids().values())
                    for xid in xids
                }
                if children_xids & loaded_xmlids:
                    # at least one child was loaded
                    keep = True
                    break
            if keep:
                continue

            # if the record has other associated xids, only remove the xid
            if self.search_count([
                ("model", "=", model),
                ("res_id", "=", res_id),
                ("id", "!=", id),
                ("id", "not in", bad_imd_ids),
            ]):
                bad_imd_ids.append(id)
                continue

            _logger.info('Deleting %s@%s (%s)', res_id, model, xmlid)
            record = Model.browse(res_id)
            if record.exists():
                module = xmlid.split('.', 1)[0]
                record = record.with_context(module=module)
                self._process_end_unlink_record(record)
            else:
                bad_imd_ids.append(id)
        if bad_imd_ids:
            self.browse(bad_imd_ids).unlink()

        # Once all views are created create specific ones
        self.env['ir.ui.view']._create_all_specific_views(modules)

        loaded_xmlids.clear()

    @api.model
    def toggle_noupdate(self, model, res_id):
        """ Toggle the noupdate flag on the external id of the record """
        record = self.env[model].browse(res_id)
        if record.check_access_rights('write'):
            for xid in self.search([('model', '=', model), ('res_id', '=', res_id)]):
                xid.noupdate = not xid.noupdate


class WizardModelMenu(models.TransientModel):
    _name = 'wizard.ir.model.menu.create'
    _description = 'Create Menu Wizard'

    menu_id = fields.Many2one('ir.ui.menu', string='Parent Menu', required=True, ondelete='cascade')
    name = fields.Char(string='Menu Name', required=True)

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
