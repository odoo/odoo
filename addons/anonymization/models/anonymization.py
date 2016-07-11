# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from itertools import groupby
from operator import itemgetter

from odoo import api, fields, models, _
from odoo.exceptions import UserError

FIELD_STATES = [('clear', 'Clear'), ('anonymized', 'Anonymized'), ('not_existing', 'Not Existing'), ('new', 'New')]
ANONYMIZATION_HISTORY_STATE = [('started', 'Started'), ('done', 'Done'), ('in_exception', 'Exception occured')]
ANONYMIZATION_DIRECTION = [('clear -> anonymized', 'clear -> anonymized'), ('anonymized -> clear', 'anonymized -> clear')]


def group(lst, cols):
    if isinstance(cols, basestring):
        cols = [cols]
    return dict((k, [v for v in itr]) for k, itr in groupby(sorted(lst, key=itemgetter(*cols)), itemgetter(*cols)))


class IrModelFieldsAnonymization(models.Model):
    _name = 'ir.model.fields.anonymization'
    _rec_name = 'field_id'

    model_name = fields.Char('Object Name', required=True)
    model_id = fields.Many2one('ir.model', string='Object', ondelete='set null')
    field_name = fields.Char(required=True)
    field_id = fields.Many2one('ir.model.fields', string='Field', ondelete='set null')
    state = fields.Selection(selection=FIELD_STATES, string='Status', required=True, readonly=True, default='clear')

    _sql_constraints = [
        ('model_id_field_id_uniq', 'unique (model_name, field_name)', _("You cannot have two fields with the same name on the same object!")),
    ]

    @api.model
    def _get_global_state(self):
        field_ids = self.search([('state', '!=', 'not_existing')])
        if not field_ids or len(field_ids) == len(field_ids.filtered(lambda field: field.state == "clear")):
            state = 'clear'  # all fields are clear
        elif len(field_ids) == len(field_ids.filtered(lambda field: field.state == "anonymized")):
            state = 'anonymized'  # all fields are anonymized
        else:
            state = 'unstable'  # fields are mixed: this should be fixed
        return state

    @api.model
    def _check_write(self):
        """check that the field is created from the menu and not from an database update
           otherwise the database update can crash:"""
        if self.env.context.get('manual'):
            global_state = self._get_global_state()
            if global_state == 'anonymized':
                raise UserError(_("The database is currently anonymized, you cannot create, modify or delete fields."))
            elif global_state == 'unstable':
                raise UserError(_("The database anonymization is currently in an unstable state. Some fields are anonymized,"
                                " while some fields are not anonymized. You should try to solve this problem before trying to create, write or delete fields."))
        return True

    @api.model
    def _get_model_and_field_ids(self, vals):
        if vals.get('field_name') and vals.get('model_name'):
            model_id = self.env['ir.model'].search([('model', '=', vals['model_name'])], limit=1).id
            if model_id:
                field_id = self.env['ir.model.fields'].search([('name', '=', vals['field_name']), ('model_id', '=', model_id)], limit=1).id
                if field_id:
                    return (model_id, field_id)
        return (False, False)

    @api.model
    def create(self, vals):
        # check field state: all should be clear before we can add a new field to anonymize:
        self._check_write()
        if vals.get('field_name') and vals.get('model_name'):
            vals['model_id'], vals['field_id'] = self._get_model_and_field_ids(vals)
        # check not existing fields:
        vals['state'] = self._get_global_state() if vals.get('field_id') else 'not_existing'
        return super(IrModelFieldsAnonymization, self).create(vals)

    @api.multi
    def write(self, vals):
        # check field state: all should be clear before we can modify a field:
        if not len(vals.keys()) == 1 and vals.get('state') == 'clear':
            self._check_write()
        if vals.get('field_name') and vals.get('model_name'):
            vals['model_id'], vals['field_id'] = self._get_model_and_field_ids(vals)
        # check not existing fields:
        if 'field_id' in vals:
            if not vals['field_id']:
                vals['state'] = 'not_existing'
            else:
                global_state = self._get_global_state()
                if global_state != 'unstable':
                    vals['state'] = global_state
        return super(IrModelFieldsAnonymization, self).write(vals)

    @api.multi
    def unlink(self):
        # check field state: all should be clear before we can unlink a field:
        self._check_write()
        return super(IrModelFieldsAnonymization, self).unlink()

    @api.onchange('model_id')
    def _onchange_model_id(self):
        self.field_name = False
        self.field_id = False
        self.model_name = self.model_id.model

    @api.onchange('model_name')
    def _onchange_model_name(self):
        self.field_name = False
        self.field_id = False
        if self.model_name:
            self.model_id = self.env['ir.model'].search([('model', '=', self.model_name)], limit=1)
        else:
            self.model_id = False

    @api.onchange('field_name')
    def _onchange_field_name(self):
        if self.field_name and self.model_name:
            self.field_id = self.env['ir.model.fields'].search([
                ('name', '=', self.field_name), ('model', '=', self.model_name)
            ], limit=1)
        else:
            self.field_id = False

    @api.onchange('field_id')
    def _onchange_field_id(self):
        self.field_name = self.field_id.name


class IrModelFieldsAnonymizationHistory(models.Model):
    _name = 'ir.model.fields.anonymization.history'
    _order = "date desc"

    date = fields.Datetime(required=True, readonly=True)
    field_ids = fields.Many2many(
        'ir.model.fields.anonymization', 'anonymized_field_to_history_rel',
        'field_id', 'history_id', string='Fields', readonly=True
    )
    state = fields.Selection(selection=ANONYMIZATION_HISTORY_STATE, string='Status', required=True, readonly=True)
    direction = fields.Selection(selection=ANONYMIZATION_DIRECTION, required=True, readonly=True)
    msg = fields.Text('Message', readonly=True)
    filepath = fields.Char('File path', readonly=True)


class IrModelFieldsAnonymizationMigrationFix(models.Model):
    _name = 'ir.model.fields.anonymization.migration.fix'
    _order = "sequence"

    target_version = fields.Char('Target Version')
    model_name = fields.Char('Model')
    field_name = fields.Char('Field')
    query = fields.Text()
    query_type = fields.Selection(selection=[('sql', 'sql'), ('python', 'python')], string='Query')
    sequence = fields.Integer()
