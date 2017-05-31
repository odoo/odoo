# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree
import os
import base64
try:
    import cPickle as pickle
except ImportError:
    import pickle
import random
import datetime
from openerp.release import version_info
from openerp.osv import fields, osv
from openerp.tools.translate import _
from openerp.tools.safe_eval import safe_eval as eval

from itertools import groupby
from operator import itemgetter
from openerp.exceptions import UserError


FIELD_STATES = [('clear', 'Clear'), ('anonymized', 'Anonymized'), ('not_existing', 'Not Existing'), ('new', 'New')]
ANONYMIZATION_STATES = FIELD_STATES + [('unstable', 'Unstable')]
WIZARD_ANONYMIZATION_STATES = [('clear', 'Clear'), ('anonymized', 'Anonymized'), ('unstable', 'Unstable')]
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


class ir_model_fields_anonymize_wizard(osv.osv_memory):
    _name = 'ir.model.fields.anonymize.wizard'

    def _get_state(self, cr, uid, ids, name, arg, context=None):
        res = {}

        state = self._get_state_value(cr, uid, context=None)
        for id in ids:
            res[id] = state

        return res

    def _get_summary(self, cr, uid, ids, name, arg, context=None):
        res = {}
        summary = self._get_summary_value(cr, uid, context)
        for id in ids:
            res[id] = summary

        return res

    _columns = {
        'name': fields.char(string='File Name'),
        'summary': fields.function(_get_summary, type='text', string='Summary'),
        'file_export': fields.binary(string='Export'),
        'file_import': fields.binary(string='Import', help="This is the file created by the anonymization process. It should have the '.pickle' extention."),
        'state': fields.function(_get_state, string='Status', type='selection', selection=WIZARD_ANONYMIZATION_STATES, readonly=False),
        'msg': fields.text(string='Message'),
    }

    def _get_state_value(self, cr, uid, context=None):
        state = self.pool.get('ir.model.fields.anonymization')._get_global_state(cr, uid, context=context)
        return state

    def _get_summary_value(self, cr, uid, context=None):
        summary = u''
        anon_field_obj = self.pool.get('ir.model.fields.anonymization')
        ir_model_fields_obj = self.pool.get('ir.model.fields')

        anon_field_ids = anon_field_obj.search(cr, uid, [('state', '<>', 'not_existing')], context=context)
        anon_fields = anon_field_obj.browse(cr, uid, anon_field_ids, context=context)

        field_ids = [anon_field.field_id.id for anon_field in anon_fields if anon_field.field_id]
        fields = ir_model_fields_obj.browse(cr, uid, field_ids, context=context)

        fields_by_id = dict([(f.id, f) for f in fields])

        for anon_field in anon_fields:
            field = fields_by_id.get(anon_field.field_id.id)
            if field:
                values = {
                    'model_name': field.model_id.name,
                    'model_code': field.model_id.model,
                    'field_code': field.name,
                    'field_name': field.field_description,
                    'state': anon_field.state,
                }
                summary += u" * %(model_name)s (%(model_code)s) -> %(field_name)s (%(field_code)s): state: (%(state)s)\n" % values
            else:
                summary += u"* Missing local model (%s) and field (%s): state: (%s) \n" % (anon_field.model_name, anon_field.field_name, anon_field.state)
        return summary

    def default_get(self, cr, uid, fields_list, context=None):
        res = {}
        res['name'] = '.pickle'
        res['summary'] = self._get_summary_value(cr, uid, context)
        res['state'] = self._get_state_value(cr, uid, context)
        res['msg'] = _("""Before executing the anonymization process, you should make a backup of your database.""")

        return res

    def fields_view_get(self, cr, uid, view_id=None, view_type='form', context=None, toolbar=False, submenu=False):
        state = self.pool.get('ir.model.fields.anonymization')._get_global_state(cr, uid, context=context)

        if context is None:
            context = {}

        step = context.get('step', 'new_window')

        res = super(ir_model_fields_anonymize_wizard, self).fields_view_get(cr, uid, view_id=view_id, view_type=view_type, context=context, toolbar=toolbar, submenu=submenu)

        eview = etree.fromstring(res['arch'])
        placeholder = eview.xpath("group[@name='placeholder1']")
        if len(placeholder):
            placeholder = placeholder[0]
            if step == 'new_window' and state == 'clear':
                # clicked in the menu and the fields are not anonymized: warn the admin that backuping the db is very important
                placeholder.addnext(etree.Element('field', {'name': 'msg', 'colspan': '4', 'nolabel': '1'}))
                placeholder.addnext(etree.Element('newline'))
                placeholder.addnext(etree.Element('label', {'string': 'Warning'}))
                eview.remove(placeholder)
            elif step == 'new_window' and state == 'anonymized':
                # clicked in the menu and the fields are already anonymized
                placeholder.addnext(etree.Element('newline'))
                placeholder.addnext(etree.Element('field', {'name': 'file_import', 'required': "1"}))
                placeholder.addnext(etree.Element('label', {'string': 'Anonymization file'}))
                eview.remove(placeholder)
            elif step == 'just_anonymized':
                # we just ran the anonymization process, we need the file export field
                placeholder.addnext(etree.Element('newline'))
                placeholder.addnext(etree.Element('field', {'name': 'file_export'}))
                # we need to remove the button:
                buttons = eview.xpath("button")
                for button in buttons:
                    eview.remove(button)
                # and add a message:
                placeholder.addnext(etree.Element('field', {'name': 'msg', 'colspan': '4', 'nolabel': '1'}))
                placeholder.addnext(etree.Element('newline'))
                placeholder.addnext(etree.Element('label', {'string': 'Result'}))
                # remove the placeholer:
                eview.remove(placeholder)
            elif step == 'just_desanonymized':
                # we just reversed the anonymization process, we don't need any field
                # we need to remove the button
                buttons = eview.xpath("button")
                for button in buttons:
                    eview.remove(button)
                # and add a message
                # and add a message:
                placeholder.addnext(etree.Element('field', {'name': 'msg', 'colspan': '4', 'nolabel': '1'}))
                placeholder.addnext(etree.Element('newline'))
                placeholder.addnext(etree.Element('label', {'string': 'Result'}))
                # remove the placeholer:
                eview.remove(placeholder)
            else:
                msg = _("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                  " while some fields are not anonymized. You should try to solve this problem before trying to do anything else.")
                raise UserError(msg)

            res['arch'] = etree.tostring(eview)

        return res

    def _raise_after_history_update(self, cr, uid, history_id, error_type, error_msg):
        self.pool.get('ir.model.fields.anonymization.history').write(cr, uid, history_id, {
            'state': 'in_exception',
            'msg': error_msg,
        })
        raise UserError('%s: %s' % (error_type, error_msg))

    def anonymize_database(self, cr, uid, ids, context=None):
        """Sets the 'anonymized' state to defined fields"""

        # create a new history record:
        anonymization_history_model = self.pool.get('ir.model.fields.anonymization.history')

        vals = {
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'state': 'started',
            'direction': 'clear -> anonymized',
        }
        history_id = anonymization_history_model.create(cr, uid, vals)

        # check that all the defined fields are in the 'clear' state
        state = self.pool.get('ir.model.fields.anonymization')._get_global_state(cr, uid, context=context)
        if state == 'anonymized':
            self._raise_after_history_update(cr, uid, history_id, _('Error !'), _("The database is currently anonymized, you cannot anonymize it again."))
        elif state == 'unstable':
            msg = _("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                  " while some fields are not anonymized. You should try to solve this problem before trying to do anything.")
            self._raise_after_history_update(cr, uid, history_id, 'Error !', msg)

        # do the anonymization:
        dirpath = os.environ.get('HOME') or os.getcwd()
        rel_filepath = 'field_anonymization_%s_%s.pickle' % (cr.dbname, history_id)
        abs_filepath = os.path.abspath(os.path.join(dirpath, rel_filepath))

        ir_model_fields_anonymization_model = self.pool.get('ir.model.fields.anonymization')
        field_ids = ir_model_fields_anonymization_model.search(cr, uid, [('state', '<>', 'not_existing')], context=context)
        fields = ir_model_fields_anonymization_model.browse(cr, uid, field_ids, context=context)

        if not fields:
            msg = "No fields are going to be anonymized."
            self._raise_after_history_update(cr, uid, history_id, 'Error !', msg)

        data = []

        for field in fields:
            model_name = field.model_id.model
            field_name = field.field_id.name
            field_type = field.field_id.ttype
            table_name = self.pool[model_name]._table

            # get the current value
            sql = "select id, \"%s\" from \"%s\"" % (field_name, table_name)
            cr.execute(sql)
            records = cr.dictfetchall()
            for record in records:
                data.append({"model_id": model_name, "field_id": field_name, "id": record['id'], "value": record[field_name]})

                # anonymize the value:
                anonymized_value = None

                sid = str(record['id'])
                if field_type == 'char':
                    anonymized_value = 'xxx'+sid
                elif field_type == 'selection':
                    anonymized_value = 'xxx'+sid
                elif field_type == 'text':
                    anonymized_value = 'xxx'+sid
                elif field_type == 'html':
                    anonymized_value = 'xxx'+sid
                elif field_type == 'boolean':
                    anonymized_value = random.choice([True, False])
                elif field_type == 'date':
                    anonymized_value = '2011-11-11'
                elif field_type == 'datetime':
                    anonymized_value = '2011-11-11 11:11:11'
                elif field_type == 'float':
                    anonymized_value = 0.0
                elif field_type == 'monetary':
                    anonymized_value = 0.0
                elif field_type == 'integer':
                    anonymized_value = 0
                elif field_type in ['binary', 'many2many', 'many2one', 'one2many', 'reference']: # cannot anonymize these kind of fields
                    msg = _("Cannot anonymize fields of these types: binary, many2many, many2one, one2many, reference.")
                    self._raise_after_history_update(cr, uid, history_id, 'Error !', msg)

                if anonymized_value is None:
                    self._raise_after_history_update(cr, uid, history_id, _('Error !'), _("Anonymized value can not be empty."))

                sql = "update \"%(table)s\" set \"%(field)s\" = %%(anonymized_value)s where id = %%(id)s" % {
                    'table': table_name,
                    'field': field_name,
                }
                cr.execute(sql, {
                    'anonymized_value': anonymized_value,
                    'id': record['id']
                })

        # save pickle:
        fn = open(abs_filepath, 'w')
        pickle.dump(data, fn, pickle.HIGHEST_PROTOCOL)

        # update the anonymization fields:
        values = {
            'state': 'anonymized',
        }
        ir_model_fields_anonymization_model.write(cr, uid, field_ids, values, context=context)

        # add a result message in the wizard:
        msgs = ["Anonymization successful.",
               "",
               "Donot forget to save the resulting file to a safe place because you will not be able to revert the anonymization without this file.",
               "",
               "This file is also stored in the %s directory. The absolute file path is: %s.",
              ]
        msg = '\n'.join(msgs) % (dirpath, abs_filepath)

        fn = open(abs_filepath, 'r')

        self.write(cr, uid, ids, {
            'msg': msg,
            'file_export': base64.encodestring(fn.read()),
        })
        fn.close()

        # update the history record:
        anonymization_history_model.write(cr, uid, history_id, {
            'field_ids': [[6, 0, field_ids]],
            'msg': msg,
            'filepath': abs_filepath,
            'state': 'done',
        })

        # handle the view:
        view_id = self.pool['ir.model.data'].xmlid_to_res_id(
            cr, uid, 'anonymization.view_ir_model_fields_anonymize_wizard_form'
        )

        return {
                'res_id': ids[0],
                'view_id': [view_id],
                'view_type': 'form',
                "view_mode": 'form',
                'res_model': 'ir.model.fields.anonymize.wizard',
                'type': 'ir.actions.act_window',
                'context': {'step': 'just_anonymized'},
                'target':'new',
        }

    def reverse_anonymize_database(self, cr, uid, ids, context=None):
        """Set the 'clear' state to defined fields"""
        ir_model_fields_anonymization_model = self.pool.get('ir.model.fields.anonymization')
        anonymization_history_model = self.pool.get('ir.model.fields.anonymization.history')

        # create a new history record:
        vals = {
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'state': 'started',
            'direction': 'anonymized -> clear',
        }
        history_id = anonymization_history_model.create(cr, uid, vals)

        # check that all the defined fields are in the 'anonymized' state
        state = ir_model_fields_anonymization_model._get_global_state(cr, uid, context=context)
        if state == 'clear':
            raise UserError(_("The database is not currently anonymized, you cannot reverse the anonymization."))
        elif state == 'unstable':
            msg = _("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                  " while some fields are not anonymized. You should try to solve this problem before trying to do anything.")
            raise UserError(msg)

        wizards = self.browse(cr, uid, ids, context=context)
        for wizard in wizards:
            if not wizard.file_import:
                msg = _("It is not possible to reverse the anonymization process without supplying the anonymization export file.")
                self._raise_after_history_update(cr, uid, history_id, 'Error !', msg)

            # reverse the anonymization:
            # load the pickle file content into a data structure:
            data = pickle.loads(base64.decodestring(wizard.file_import))

            migration_fix_obj = self.pool.get('ir.model.fields.anonymization.migration.fix')
            fix_ids = migration_fix_obj.search(cr, uid, [('target_version', '=', '.'.join(map(str, version_info[:2])))])
            fixes = migration_fix_obj.read(cr, uid, fix_ids, ['model_name', 'field_name', 'query', 'query_type', 'sequence'])
            fixes = group(fixes, ('model_name', 'field_name'))

            for line in data:
                queries = []
                table_name = self.pool[line['model_id']]._table if line['model_id'] in self.pool else None

                # check if custom sql exists:
                key = (line['model_id'], line['field_id'])
                custom_updates =  fixes.get(key)
                if custom_updates:
                    custom_updates.sort(key=itemgetter('sequence'))
                    queries = [(record['query'], record['query_type']) for record in custom_updates if record['query_type']]
                elif table_name:
                    queries = [("update \"%(table)s\" set \"%(field)s\" = %%(value)s where id = %%(id)s" % {
                        'table': table_name,
                        'field': line['field_id'],
                    }, 'sql')]

                for query in queries:
                    if query[1] == 'sql':
                        sql = query[0]
                        cr.execute(sql, {
                            'value': line['value'],
                            'id': line['id']
                        })
                    elif query[1] == 'python':
                        raw_code = query[0]
                        code = raw_code % line
                        eval(code)
                    else:
                        raise Exception("Unknown query type '%s'. Valid types are: sql, python." % (query['query_type'], ))

            # update the anonymization fields:
            ir_model_fields_anonymization_model = self.pool.get('ir.model.fields.anonymization')
            field_ids = ir_model_fields_anonymization_model.search(cr, uid, [('state', '<>', 'not_existing')], context=context)
            values = {
                'state': 'clear',
            }
            ir_model_fields_anonymization_model.write(cr, uid, field_ids, values, context=context)

            # add a result message in the wizard:
            msg = '\n'.join(["Successfully reversed the anonymization.",
                             "",
                            ])

            self.write(cr, uid, ids, {'msg': msg})

            # update the history record:
            anonymization_history_model.write(cr, uid, history_id, {
                'field_ids': [[6, 0, field_ids]],
                'msg': msg,
                'filepath': False,
                'state': 'done',
            })

            # handle the view:
            view_id = self.pool['ir.model.data'].xmlid_to_res_id(
                cr, uid, 'anonymization.view_ir_model_fields_anonymize_wizard_form'
            )


            return {
                    'res_id': ids[0],
                    'view_id': [view_id],
                    'view_type': 'form',
                    "view_mode": 'form',
                    'res_model': 'ir.model.fields.anonymize.wizard',
                    'type': 'ir.actions.act_window',
                    'context': {'step': 'just_desanonymized'},
                    'target':'new',
            }

    def _id_get(self, cr, uid, model, id_str, mod):
        if '.' in id_str:
            mod, id_str = id_str.split('.')
        try:
            idn = self.pool.get('ir.model.data')._get_id(cr, uid, mod, id_str)
            res = int(self.pool.get('ir.model.data').read(cr, uid, [idn], ['res_id'])[0]['res_id'])
        except:
            res = None
        return res


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
