# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from dateutil.relativedelta import relativedelta


class DataCleaningBase(models.Model):
    _name = 'data_cleaning.base'
    _description = 'Data Cleaning Base Model'
    _order = 'sequence, id'

    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False, required=True, copy=True)
    active = fields.Boolean(default=True)

    res_model_id = fields.Many2one('ir.model', string='Model', required=True, ondelete='cascade', index=True)
    res_model_name = fields.Char(related='res_model_id.model', string='Model Name', readonly=True, store=True)

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

    recycle_ids = fields.One2many(
        'data_recycle.model',
        'base_id',
        string='Recycle Rules',
        context={'active_test': False}
    )

    _check_notif_freq = models.Constraint(
        'CHECK(notify_frequency > 0)',
        'The notification frequency should be greater than 0',
    )

    @api.depends('res_model_id')
    def _compute_name(self):
        for model in self:
            if not model.name:
                model.name = model.res_model_id.name

    @api.onchange('cleaning_mode')
    def _onchange_cleaning_mode(self):
        if self.cleaning_mode == 'automatic':
            return {
                'warning': {
                    'title': "Automatic Mode",
                    'message': "When enabling automatic mode your rules will run periodically without manual validation. "
                               "Please note that these changes are permanent and cannot be reversed."
                }
            }

    def write(self, vals):
        result = super().write(vals)

        # Keep recycle records in sync with the base record's archived state.
        # (Recycle models already follow the base `active` through their related field.)
        if 'active' in vals:
            self.with_context(active_test=False).recycle_ids.recycle_record_ids.write({'active': vals['active']})

        self._refresh_records_to_process(vals)
        return result

    def _refresh_records_to_process(self, vals):
        """Hook to regenerate the records backing the "to process" counts when the matching configuration changes."""
        if not {'res_model_id', 'cleaning_mode'}.isdisjoint(vals):
            self.recycle_ids.sudo()._recycle_records()

    def _cron_run_cleaning(self):
        records = self.sudo().search([])
        self.sudo()._perform_cleaning(records)
        records._notify_records()

    @api.model
    def _perform_cleaning(self, records):
        """Hook method meant to be extended by other modules."""
        records.recycle_ids._recycle_records(batch_commits=True)

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
                record._notify_related_records(delta)

    def _notify_related_records(self, delta):
        """Hook method meant to be extended by other modules."""
        for recycle in self.recycle_ids:
            self._send_notification(
                delta,
                record_model='data_recycle.record',
                domain_field='recycle_model_id',
                record_id=recycle.id,
                action='data_recycle.action_data_recycle_record_notification',
                rule_type=self.env._("recycling"),
                subject=self.env._("Data to Recycle"),
            )

    def _send_notification(self, delta, *, record_model, domain_field, record_id, action, rule_type, subject):
        """Notify the configured users about pending records linked to this rule.

        Counts records of ``record_model`` linked through ``domain_field`` to ``record_id``
        and created within ``delta``, then posts a message. ``rule_type`` is the only varying word in
        the body (e.g. 'recycling', 'field cleaning', 'deduplication') and ``action`` is the
        xmlid the "here" link redirects to.
        """
        self.ensure_one()
        last_date = fields.Date.today() - delta
        records_count = self.env[record_model].search_count([
            (domain_field, '=', record_id),
            ('create_date', '>=', last_date),
        ])
        if not records_count:
            return
        menu_id = self.env.ref('data_recycle.menu_data_cleaning_root').id
        self.env['mail.thread'].sudo().message_notify(
            body=self.env['ir.qweb']._render('data_recycle.notification', {
                'records_count': records_count,
                'res_model_label': self.res_model_id.name,
                'rule_type': rule_type,
                'link': '/odoo/%s/action-%s?menu_id=%s' % (record_id, action, menu_id),
            }),
            model=self._name,
            partner_ids=self.notify_user_ids.partner_id.ids,
            res_id=self.id,
            subject=subject,
        )
