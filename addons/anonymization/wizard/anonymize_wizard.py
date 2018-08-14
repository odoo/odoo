# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import os
import random

from lxml import etree
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.release import version_info
from odoo.tools import pickle
from odoo.tools.safe_eval import safe_eval
from odoo.addons.anonymization.models.anonymization import group

WIZARD_ANONYMIZATION_STATES = [('clear', 'Clear'), ('anonymized', 'Anonymized'), ('unstable', 'Unstable')]


class IrModelFieldsAnonymizeWizard(models.TransientModel):
    _name = 'ir.model.fields.anonymize.wizard'

    name = fields.Char('File Name')
    summary = fields.Text(compute='_compute_summary')
    file_export = fields.Binary('Export')
    file_import = fields.Binary('Import',
        help="This is the file created by the anonymization process. It should have the '.pickle' extention.")
    state = fields.Selection(compute='_compute_state', string='Status', selection=WIZARD_ANONYMIZATION_STATES)
    msg = fields.Text('Message')

    @api.multi
    def _compute_summary(self):
        for anonymize_wizard in self:
            anonymize_wizard.summary = anonymize_wizard._get_summary_value()

    @api.multi
    def _compute_state(self):
        for anonymize_wizard in self:
            anonymize_wizard.state = anonymize_wizard._get_state_value()

    @api.model
    def _get_state_value(self):
        return self.env['ir.model.fields.anonymization']._get_global_state()

    @api.model
    def _get_summary_value(self):
        summary = u''
        for anon_field in self.env['ir.model.fields.anonymization'].search([('state', '!=', 'not_existing')]):
            field = anon_field.field_id
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

    @api.model
    def default_get(self, fields_list):
        res = {}
        res['name'] = '.pickle'
        res['summary'] = self._get_summary_value()
        res['state'] = self._get_state_value()
        res['msg'] = _("Before executing the anonymization process, you should make a backup of your database.")
        return res

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        state = self.env['ir.model.fields.anonymization']._get_global_state()
        step = self.env.context.get('step', 'new_window')
        res = super(IrModelFieldsAnonymizeWizard, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
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
                placeholder.addnext(etree.Element('field', {'name': 'msg', 'colspan': '4', 'nolabel': '1'}))
                placeholder.addnext(etree.Element('newline'))
                placeholder.addnext(etree.Element('label', {'string': 'Result'}))
                # remove the placeholer:
                eview.remove(placeholder)
            else:
                raise UserError(_("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                                  " while some fields are not anonymized. You should try to solve this problem before trying to do anything else."))
            res['arch'] = etree.tostring(eview)
        return res

    @api.multi
    def anonymize_database(self):
        """Sets the 'anonymized' state to defined fields"""
        # pylint: disable=W0101
        raise UserError("""The Odoo Migration Platform no longer accepts anonymized databases.\n
            If you wish for your data to remain private during migration, please contact us at upgrade@odoo.com""")
        self.ensure_one()

        # create a new history record:
        history = self.env['ir.model.fields.anonymization.history'].create({
            'date': fields.Datetime.now(),
            'state': 'started',
            'direction': 'clear -> anonymized'
        })

        # check that all the defined fields are in the 'clear' state
        state = self.env['ir.model.fields.anonymization']._get_global_state()
        error_type = _('Error !')
        if state == 'anonymized':
            raise UserError('%s: %s' % (error_type, _("The database is currently anonymized, you cannot anonymize it again.")))
        elif state == 'unstable':
            raise UserError('%s: %s' % (error_type, _("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                                                      " while some fields are not anonymized. You should try to solve this problem before trying to do anything.")))

        # do the anonymization:
        dirpath = os.environ.get('HOME') or os.getcwd()
        rel_filepath = 'field_anonymization_%s_%s.pickle' % (self.env.cr.dbname, history.id)
        abs_filepath = os.path.abspath(os.path.join(dirpath, rel_filepath))

        ano_fields = self.env['ir.model.fields.anonymization'].search([('state', '!=', 'not_existing')])
        if not ano_fields:
            raise UserError('%s: %s' % (error_type, _("No fields are going to be anonymized.")))

        data = []

        for field in ano_fields:
            model_name = field.model_id.model
            field_name = field.field_id.name
            field_type = field.field_id.ttype
            table_name = self.env[model_name]._table

            # get the current value
            self.env.cr.execute('select id, "%s" from "%s"' % (field_name, table_name))
            for record in self.env.cr.dictfetchall():
                data.append({"model_id": model_name, "field_id": field_name, "id": record['id'], "value": record[field_name]})

                # anonymize the value:
                anonymized_value = None

                sid = str(record['id'])
                if field_type == 'char':
                    anonymized_value = 'xxx' + sid
                elif field_type == 'selection':
                    anonymized_value = 'xxx' + sid
                elif field_type == 'text':
                    anonymized_value = 'xxx' + sid
                elif field_type == 'html':
                    anonymized_value = 'xxx' + sid
                elif field_type == 'boolean':
                    anonymized_value = random.choice([True, False])
                elif field_type == 'date':
                    anonymized_value = '2011-11-11'
                elif field_type == 'datetime':
                    anonymized_value = '2011-11-11 11:11:11'
                elif field_type in ('float', 'monetary'):
                    anonymized_value = 0.0
                elif field_type == 'integer':
                    anonymized_value = 0
                elif field_type in ['binary', 'many2many', 'many2one', 'one2many', 'reference']:  # cannot anonymize these kind of fields
                    raise UserError('%s: %s' % (error_type, _("Cannot anonymize fields of these types: binary, many2many, many2one, one2many, reference.")))

                if anonymized_value is None:
                    raise UserError('%s: %s' % (error_type, _("Anonymized value can not be empty.")))

                sql = 'update "%(table)s" set "%(field)s" = %%(anonymized_value)s where id = %%(id)s' % {
                    'table': table_name,
                    'field': field_name,
                }
                self.env.cr.execute(sql, {
                    'anonymized_value': anonymized_value,
                    'id': record['id']
                })

        # save pickle:
        fn = open(abs_filepath, 'w')
        pickle.dump(data, fn, protocol=-1)

        # update the anonymization fields:
        ano_fields.write({'state': 'anonymized'})

        # add a result message in the wizard:
        msgs = ["Anonymization successful.",
                "",
                "Donot forget to save the resulting file to a safe place because you will not be able to revert the anonymization without this file.",
                "",
                "This file is also stored in the %s directory. The absolute file path is: %s."
               ]
        msg = '\n'.join(msgs) % (dirpath, abs_filepath)

        fn = open(abs_filepath, 'r')

        self.write({
            'msg': msg,
            'file_export': base64.encodestring(fn.read()),
        })
        fn.close()

        # update the history record:
        history.write({
            'field_ids': [[6, 0, ano_fields.ids]],
            'msg': msg,
            'filepath': abs_filepath,
            'state': 'done',
        })

        return {
            'res_id': self.id,
            'view_id': self.env.ref('anonymization.view_ir_model_fields_anonymize_wizard_form').ids,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'ir.model.fields.anonymize.wizard',
            'type': 'ir.actions.act_window',
            'context': {'step': 'just_anonymized'},
            'target': 'new'
        }

    @api.multi
    def reverse_anonymize_database(self):
        """Set the 'clear' state to defined fields"""
        self.ensure_one()
        IrModelFieldsAnonymization = self.env['ir.model.fields.anonymization']

        # check that all the defined fields are in the 'anonymized' state
        state = IrModelFieldsAnonymization._get_global_state()
        if state == 'clear':
            raise UserError(_("The database is not currently anonymized, you cannot reverse the anonymization."))
        elif state == 'unstable':
            raise UserError(_("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                              " while some fields are not anonymized. You should try to solve this problem before trying to do anything."))

        if not self.file_import:
            raise UserError('%s: %s' % (_('Error !'), _("It is not possible to reverse the anonymization process without supplying the anonymization export file.")))

        # reverse the anonymization:
        # load the pickle file content into a data structure:
        data = pickle.loads(base64.decodestring(self.file_import))

        fixes = self.env['ir.model.fields.anonymization.migration.fix'].search_read([
            ('target_version', '=', '.'.join(map(str, version_info[:2])))
        ], ['model_name', 'field_name', 'query', 'query_type', 'sequence'])
        fixes = group(fixes, ('model_name', 'field_name'))

        for line in data:
            queries = []
            table_name = self.env[line['model_id']]._table if line['model_id'] in self.env else None

            # check if custom sql exists:
            key = (line['model_id'], line['field_id'])
            custom_updates = fixes.get(key)
            if custom_updates:
                custom_updates.sort(key=itemgetter('sequence'))
                queries = [(record['query'], record['query_type']) for record in custom_updates if record['query_type']]
            elif table_name:
                queries = [('update "%(table)s" set "%(field)s" = %%(value)s where id = %%(id)s' % {
                    'table': table_name,
                    'field': line['field_id'],
                }, 'sql')]

            for query in queries:
                if query[1] == 'sql':
                    self.env.cr.execute(query[0], {
                        'value': line['value'],
                        'id': line['id']
                    })
                elif query[1] == 'python':
                    safe_eval(query[0] % line)
                else:
                    raise Exception("Unknown query type '%s'. Valid types are: sql, python." % (query['query_type'], ))

        # update the anonymization fields:
        ano_fields = IrModelFieldsAnonymization.search([('state', '!=', 'not_existing')])
        ano_fields.write({'state': 'clear'})

        # add a result message in the wizard:
        self.msg = '\n'.join(["Successfully reversed the anonymization.", ""])

        # create a new history record:
        history = self.env['ir.model.fields.anonymization.history'].create({
            'date': fields.Datetime.now(),
            'field_ids': [[6, 0, ano_fields.ids]],
            'msg': self.msg,
            'filepath': False,
            'direction': 'anonymized -> clear',
            'state': 'done'
        })

        return {
            'res_id': self.id,
            'view_id': self.env.ref('anonymization.view_ir_model_fields_anonymize_wizard_form').ids,
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'ir.model.fields.anonymize.wizard',
            'type': 'ir.actions.act_window',
            'context': {'step': 'just_desanonymized'},
            'target': 'new'
        }
