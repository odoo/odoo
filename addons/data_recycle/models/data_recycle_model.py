# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from collections import defaultdict
from dateutil.relativedelta import relativedelta

from odoo import api, fields, models, modules
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.tools import _, split_every

# When recycle_mode = automatic, _recycle_records calls action_validate.
# This is quite slow so requires smaller batch size.
DR_CREATE_STEP_AUTO = 5000
DR_CREATE_STEP_MANUAL = 50000


class Data_RecycleModel(models.Model):
    _name = 'data_recycle.model'
    _description = 'Recycling Model'
    _order = 'name'


    unified_id = fields.Many2one('data_cleaning.unified', string='Unified Model', required=True, ondelete='cascade')
    name = fields.Char(related='unified_id.name', string='Name', readonly=True)
    res_model_id = fields.Many2one(related='unified_id.res_model_id', string='Model', readonly=True)
    res_model_name = fields.Char(related='unified_id.res_model_name', string='Model Name', readonly=True)
    
    active = fields.Boolean(related='unified_id.active', readonly=False)
    recycle_mode = fields.Selection(related='unified_id.cleaning_mode', string='Recycle Mode', readonly=False)
    
    recycle_record_ids = fields.One2many('data_recycle.record', 'recycle_model_id')
    recycle_action = fields.Selection([
        ('archive', 'Archive'),
        ('unlink', 'Delete'),
    ], string="Recycle Action", default='unlink', required=True)

    # Rule
    domain = fields.Char(string="Filter", compute='_compute_domain', readonly=False, store=True)
    time_field_id = fields.Many2one(
        'ir.model.fields', string='Time Field',
        domain="[('model_id', '=', res_model_id), ('ttype', 'in', ('date', 'datetime')), ('store', '=', True)]",
        ondelete='cascade')
    time_field_delta = fields.Integer(string='Delta', default=1)
    time_field_delta_unit = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
        ('years', 'Years')], string='Delta Unit', default='months')
    include_archived = fields.Boolean()

    records_to_recycle_count = fields.Integer(
        'Records To Recycle', compute='_compute_records_to_recycle_count')

    # User Notifications for Manual clean
    notify_user_ids = fields.Many2many(related='unified_id.notify_user_ids', readonly=False)
    notify_frequency = fields.Integer(related='unified_id.notify_frequency', readonly=False)
    notify_frequency_period = fields.Selection(related='unified_id.notify_frequency_period', readonly=False)
    last_notification = fields.Datetime(related='unified_id.last_notification', readonly=True)


    @api.constrains('recycle_action')
    def _check_recycle_action(self):
        for model in self:
            if model.recycle_action == 'archive' and 'active' not in self.env[model.res_model_name]:
                raise UserError(_("This model doesn't manage archived records. Only deletion is possible."))

    @api.depends('res_model_id')
    def _compute_domain(self):
        self.domain = '[]'

    # Removed _compute_name as name is now related

    def _compute_records_to_recycle_count(self):
        count_data = self.env['data_recycle.record']._read_group(
            [('recycle_model_id', 'in', self.ids)],
            ['recycle_model_id'],
            ['__count'])
        counts = {recycle_model.id: count for recycle_model, count in count_data}
        for model in self:
            model.records_to_recycle_count = counts[model.id] if model.id in counts else 0

    def _recycle_records(self, batch_commits=False):
        self.env.flush_all()
        records_to_clean = []
        is_test = modules.module.current_test

        existing_recycle_records = self.env['data_recycle.record'].with_context(
            active_test=False).search([('recycle_model_id', 'in', self.ids)])
        mapped_existing_records = defaultdict(list)
        for recycle_record in existing_recycle_records:
            mapped_existing_records[recycle_record.recycle_model_id].append(recycle_record.res_id)

        for recycle_model in self:
            rule_domain = Domain(ast.literal_eval(recycle_model.domain)) if recycle_model.domain and recycle_model.domain != '[]' else Domain.TRUE
            if recycle_model.time_field_id and recycle_model.time_field_delta and recycle_model.time_field_delta_unit:
                if recycle_model.time_field_id.ttype == 'date':
                    now = fields.Date.today()
                else:
                    now = fields.Datetime.now()
                delta = relativedelta(**{recycle_model.time_field_delta_unit: recycle_model.time_field_delta})
                rule_domain &= Domain(recycle_model.time_field_id.name, '<=', now - delta)
            model = self.env[recycle_model.res_model_name]
            if recycle_model.include_archived:
                model = model.with_context(active_test=False)
            records_to_recycle = model.search(rule_domain)
            records_to_create = [{
                'res_id': record.id,
                'recycle_model_id': recycle_model.id,
            } for record in records_to_recycle if record.id not in mapped_existing_records[recycle_model]]

            if recycle_model.recycle_mode == 'automatic':
                for records_to_create_batch in split_every(DR_CREATE_STEP_AUTO, records_to_create):
                    self.env['data_recycle.record'].create(records_to_create_batch).action_validate()
                    if batch_commits and not is_test:
                        # Commit after each batch iteration to avoid complete rollback on timeout as
                        # this can create lots of new records.
                        self.env.cr.commit()
            else:
                records_to_clean = records_to_clean + records_to_create
        for records_to_clean_batch in split_every(DR_CREATE_STEP_MANUAL, records_to_clean):
            self.env['data_recycle.record'].create(records_to_clean_batch)
            if batch_commits and not is_test:
                self.env.cr.commit()

    def _send_notification(self, delta):
        self.ensure_one()
        last_date = fields.Date.today() - delta
        records_count = self.env['data_recycle.record'].search_count([
            ('recycle_model_id', '=', self.id),
            ('create_date', '>=', last_date)
        ])
        partner_ids = self.notify_user_ids.partner_id.ids if records_count else []
        if partner_ids:
            menu_id = self.env.ref('data_recycle.menu_data_cleaning_root').id
            self.env['mail.thread'].message_notify(
                body=self.env['ir.qweb']._render(
                    'data_recycle.notification',
                    {
                        'records_count': records_count,
                        'res_model_label': self.res_model_id.name,
                        'recycle_model_id': self.id,
                        'menu_id': menu_id
                    }
                ),
                model=self._name,
                partner_ids=partner_ids,
                res_id=self.id,
                subject=_('Data to Recycle'),
            )

    def write(self, vals):
        if 'active' in vals and not vals['active']:
            self.env['data_recycle.record'].search([('recycle_model_id', 'in', self.ids)]).unlink()
        return super().write(vals)

    def open_records(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("data_recycle.action_data_recycle_record")
        action['context'] = dict(ast.literal_eval(action.get('context')), searchpanel_default_recycle_model_id=self.id)
        return action

    def action_recycle_records(self):
        self.sudo()._recycle_records()
        if self.recycle_mode == 'manual':
            return self.open_records()
        return
