# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.osv import fields, osv
from openerp.tools.translate import _

from itertools import groupby
from operator import itemgetter
from openerp.exceptions import UserError


FIELD_STATES = [('clear', 'Clear'), ('anonymized', 'Anonymized'), ('not_existing', 'Not Existing'), ('new', 'New')]
ANONYMIZATION_HISTORY_STATE = [('started', 'Started'), ('done', 'Done'), ('in_exception', 'Exception occured')]
ANONYMIZATION_DIRECTION = [('clear -> anonymized', 'clear -> anonymized'), ('anonymized -> clear', 'anonymized -> clear')]


def group(lst, cols):
    if isinstance(cols, basestring):
        cols = [cols]
    return dict((k, [v for v in itr]) for k, itr in groupby(sorted(lst, key=itemgetter(*cols)), itemgetter(*cols)))


class ir_model_fields_anonymization(osv.osv):
    _name = 'ir.model.fields.anonymization'
    _rec_name = 'field_id'

    _columns = {
        'model_name': fields.char('Object Name', required=True),
        'model_id': fields.many2one('ir.model', 'Object', ondelete='set null'),
        'field_name': fields.char('Field Name', required=True),
        'field_id': fields.many2one('ir.model.fields', 'Field', ondelete='set null'),
        'state': fields.selection(selection=FIELD_STATES, String='Status', required=True, readonly=True),
    }

    _sql_constraints = [
        ('model_id_field_id_uniq', 'unique (model_name, field_name)', _("You cannot have two fields with the same name on the same object!")),
    ]

    def _get_global_state(self, cr, uid, context=None):
        ids = self.search(cr, uid, [('state', '<>', 'not_existing')], context=context)
        fields = self.browse(cr, uid, ids, context=context)
        if not len(fields) or len(fields) == len([f for f in fields if f.state == 'clear']):
            state = 'clear' # all fields are clear
        elif len(fields) == len([f for f in fields if f.state == 'anonymized']):
            state = 'anonymized' # all fields are anonymized
        else:
            state = 'unstable' # fields are mixed: this should be fixed

        return state

    def _check_write(self, cr, uid, context=None):
        """check that the field is created from the menu and not from an database update
           otherwise the database update can crash:"""
        if context is None:
            context = {}

        if context.get('manual'):
            global_state = self._get_global_state(cr, uid, context=context)
            if global_state == 'anonymized':
                raise UserError(_("The database is currently anonymized, you cannot create, modify or delete fields."))
            elif global_state == 'unstable':
                msg = _("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                      " while some fields are not anonymized. You should try to solve this problem before trying to create, write or delete fields.")
                raise UserError(msg)

        return True

    def _get_model_and_field_ids(self, cr, uid, vals, context=None):
        model_and_field_ids = (False, False)

        if 'field_name' in vals and vals['field_name'] and 'model_name' in vals and vals['model_name']:
            ir_model_fields_obj = self.pool.get('ir.model.fields')
            ir_model_obj = self.pool.get('ir.model')

            model_ids = ir_model_obj.search(cr, uid, [('model', '=', vals['model_name'])], context=context)
            if model_ids:
                field_ids = ir_model_fields_obj.search(cr, uid, [('name', '=', vals['field_name']), ('model_id', '=', model_ids[0])], context=context)
                if field_ids:
                    field_id = field_ids[0]
                    model_and_field_ids = (model_ids[0], field_id)

        return model_and_field_ids

    def create(self, cr, uid, vals, context=None):
        # check field state: all should be clear before we can add a new field to anonymize:
        self._check_write(cr, uid, context=context)

        global_state = self._get_global_state(cr, uid, context=context)

        if 'field_name' in vals and vals['field_name'] and 'model_name' in vals and vals['model_name']:
            vals['model_id'], vals['field_id'] = self._get_model_and_field_ids(cr, uid, vals, context=context)

        # check not existing fields:
        if not vals.get('field_id'):
            vals['state'] = 'not_existing'
        else:
            vals['state'] = global_state

        res = super(ir_model_fields_anonymization, self).create(cr, uid, vals, context=context)

        return res

    def write(self, cr, uid, ids, vals, context=None):
        # check field state: all should be clear before we can modify a field:
        if not (len(vals.keys()) == 1 and vals.get('state') == 'clear'):
            self._check_write(cr, uid, context=context)

        if 'field_name' in vals and vals['field_name'] and 'model_name' in vals and vals['model_name']:
            vals['model_id'], vals['field_id'] = self._get_model_and_field_ids(cr, uid, vals, context=context)

        # check not existing fields:
        if 'field_id' in vals:
            if not vals.get('field_id'):
                vals['state'] = 'not_existing'
            else:
                global_state = self._get_global_state(cr, uid, context)
                if global_state != 'unstable':
                    vals['state'] = global_state

        res = super(ir_model_fields_anonymization, self).write(cr, uid, ids, vals, context=context)

        return res

    def unlink(self, cr, uid, ids, context=None):
        # check field state: all should be clear before we can unlink a field:
        self._check_write(cr, uid, context=context)

        res = super(ir_model_fields_anonymization, self).unlink(cr, uid, ids, context=context)
        return res

    def onchange_model_id(self, cr, uid, ids, model_id, context=None):
        res = {'value': {
                    'field_name': False,
                    'field_id': False,
                    'model_name': False,
              }}

        if model_id:
            ir_model_obj = self.pool.get('ir.model')
            model_ids = ir_model_obj.search(cr, uid, [('id', '=', model_id)])
            model_id = model_ids and model_ids[0] or None
            model_name = model_id and ir_model_obj.browse(cr, uid, model_id).model or False
            res['value']['model_name'] = model_name

        return res

    def onchange_model_name(self, cr, uid, ids, model_name, context=None):
        res = {'value': {
                    'field_name': False,
                    'field_id': False,
                    'model_id': False,
              }}

        if model_name:
            ir_model_obj = self.pool.get('ir.model')
            model_ids = ir_model_obj.search(cr, uid, [('model', '=', model_name)])
            model_id = model_ids and model_ids[0] or False
            res['value']['model_id'] = model_id

        return res

    def onchange_field_name(self, cr, uid, ids, field_name, model_name):
        res = {'value': {
                'field_id': False,
            }}

        if field_name and model_name:
            ir_model_fields_obj = self.pool.get('ir.model.fields')
            field_ids = ir_model_fields_obj.search(cr, uid, [('name', '=', field_name), ('model', '=', model_name)])
            field_id = field_ids and field_ids[0] or False
            res['value']['field_id'] = field_id

        return res

    def onchange_field_id(self, cr, uid, ids, field_id, model_name):
        res = {'value': {
                    'field_name': False,
              }}

        if field_id:
            ir_model_fields_obj = self.pool.get('ir.model.fields')
            field = ir_model_fields_obj.browse(cr, uid, field_id)
            res['value']['field_name'] = field.name

        return res

    _defaults = {
        'state': lambda *a: 'clear',
    }


class ir_model_fields_anonymization_history(osv.osv):
    _name = 'ir.model.fields.anonymization.history'
    _order = "date desc"

    _columns = {
        'date': fields.datetime('Date', required=True, readonly=True),
        'field_ids': fields.many2many('ir.model.fields.anonymization', 'anonymized_field_to_history_rel', 'field_id', 'history_id', 'Fields', readonly=True),
        'state': fields.selection(selection=ANONYMIZATION_HISTORY_STATE, string='Status', required=True, readonly=True),
        'direction': fields.selection(selection=ANONYMIZATION_DIRECTION, string='Direction', size=20, required=True, readonly=True),
        'msg': fields.text('Message', readonly=True),
        'filepath': fields.char(string='File path', readonly=True),
    }


class ir_model_fields_anonymization_migration_fix(osv.osv):
    _name = 'ir.model.fields.anonymization.migration.fix'
    _order = "sequence"

    _columns = {
        'target_version': fields.char('Target Version'),
        'model_name': fields.char('Model'),
        'field_name': fields.char('Field'),
        'query': fields.text('Query'),
        'query_type': fields.selection(string='Query', selection=[('sql', 'sql'), ('python', 'python')]),
        'sequence': fields.integer('Sequence'),
    }
