# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class DataCleaningUnified(models.Model):
    _name = 'data_cleaning.unified'
    _description = 'Unified Data Cleaning Model'
    _order = 'name'

    name = fields.Char(
        string='Name', compute='_compute_name', store=True, readonly=False, required=True, copy=True)
    active = fields.Boolean(default=True)
    
    res_model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade')
    res_model_name = fields.Char(
        related='res_model_id.model', string='Model Name', readonly=True, store=True)

    cleaning_mode = fields.Selection([
        ('manual', 'Manual'),
        ('automatic', 'Automatic'),
    ], string='Cleaning Mode', default='manual', required=True)

    # User Notifications for Manual clean
    notify_user_ids = fields.Many2many(
        'res.users', string='Notify Users',
        domain=lambda self: [('all_group_ids', 'in', self.env.ref('base.group_system').id)],
        default=lambda self: self.env.user,
        help='List of users to notify when there are new records to clean')
    notify_frequency = fields.Integer(string='Notify', default=1)
    notify_frequency_period = fields.Selection([
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months')], string='Notify Frequency Period', default='weeks')
    last_notification = fields.Datetime(readonly=True)

    recycle_ids = fields.One2many('data_recycle.model', 'unified_id', string='Recycle Rules')

    _check_notif_freq = models.Constraint(
        'CHECK(notify_frequency > 0)',
        'The notification frequency should be greater than 0',
    )

    @api.depends('res_model_id')
    def _compute_name(self):
        for model in self:
            if not model.name:
                model.name = model.res_model_id.name if model.res_model_id else ''


    def _cron_run_cleaning(self):
        records = self.search([])
        records.recycle_ids._recycle_records(batch_commits=True)
        records._notify_records()


    def _notify_records(self):
        for record in self:
            if record.cleaning_mode == 'automatic':
                continue
            if not record.notify_user_ids or not record.notify_frequency:
                continue

            if record.notify_frequency_period == 'days':
                delta = relativedelta(days=record.notify_frequency)
            elif record.notify_frequency_period == 'weeks':
                delta = relativedelta(weeks=record.notify_frequency)
            else:
                delta = relativedelta(months=record.notify_frequency)

            if not record.last_notification or (record.last_notification + delta) < fields.Datetime.now():
                record.last_notification = fields.Datetime.now()
                # Notify for recycle records
                for recycle in record.recycle_ids:
                    recycle._send_notification(delta)

