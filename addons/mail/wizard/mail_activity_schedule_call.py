# Part of Odoo. See LICENSE file for full copyright and licensing details.

import ast

from odoo import api, fields, models
from odoo.fields import Domain


class MailActivityScheduleCall(models.TransientModel):
    """ The activity scheduling wizard, as opened to log a call that took place on a
    document. """
    _name = 'mail.activity.schedule.call'
    _inherit = 'mail.activity.schedule'
    _description = 'Log a call as an activity in a chatter'

    activity_type_id_domain = fields.Char(
        compute='_compute_activity_type_id_domain', export_string_translation=False)
    call_history_id = fields.Many2one('discuss.call.history', export_string_translation=False)
    contact_id = fields.Many2one(
        'res.partner', compute='_compute_contact_id', readonly=False)
    contact_id_domain = fields.Char(
        compute='_compute_contact_id_domain', export_string_translation=False)
    is_call_ongoing = fields.Boolean(
        compute='_compute_is_call_ongoing', export_string_translation=False)
    res_model_selection = fields.Selection(
        selection='_selection_res_model', string="Related Model",
        inverse='_inverse_res_model_selection', store=False)

    @api.depends(lambda self: ('res_model_selection', *self._get_res_model_fields().values()))
    def _compute_res_ids(self):
        super()._compute_res_ids()
        fields_map = self._get_res_model_fields()
        for scheduler in self:
            field_name = fields_map.get(scheduler.res_model_selection)
            if not field_name:
                continue
            record = scheduler[field_name]
            scheduler.res_ids = f"{[record.id]}" if record else False

    @api.depends_context('log_activity_category')
    @api.depends('res_model_selection')
    def _compute_activity_type_id_domain(self):
        category = self.env.context.get('log_activity_category')
        for scheduler in self:
            # res_model is not reliable here, compute it from res_model_selection instead
            res_model = scheduler._get_res_model_from_selection(scheduler.res_model_selection)
            domain = Domain('res_model', '=', res_model) | Domain('res_model', '=', False)
            if category:
                domain &= Domain('category', '=', category)
            scheduler.activity_type_id_domain = domain

    @api.depends('res_model_selection', 'contact_id_domain')
    @api.depends_context('log_contact_id')
    def _compute_contact_id(self):
        for scheduler in self:
            if scheduler.contact_id or scheduler.res_model_selection != 'res.partner':
                continue
            domain = ast.literal_eval(scheduler.contact_id_domain or '[]')
            scheduler.contact_id = self.env.context.get('log_contact_id') or self._get_log_default_record(
                'res.partner', domain,
            )

    @api.depends_context('log_contact_id', 'log_channel_partner_ids')
    def _compute_contact_id_domain(self):
        # restrict the contacts to the commercial entity of the one the call was made
        # with: the call may be logged on any of its contacts, not just on that one
        if contact := self._get_log_filter_contact():
            domain = [('id', 'child_of', contact.commercial_partner_id.ids)]
        else:
            domain = []
        self.contact_id_domain = domain

    @api.depends(lambda self: self._get_logged_call_depends())
    def _compute_is_call_ongoing(self):
        for scheduler in self:
            call = scheduler._get_logged_call()
            scheduler.is_call_ongoing = bool(call) and call._is_call_ongoing()

    def _inverse_res_model_selection(self):
        """ Sync res_model when the user changes res_model_selection """
        for scheduler in self.filtered('res_model_selection'):
            scheduler.res_model = scheduler._get_res_model_from_selection(scheduler.res_model_selection)

    def action_schedule_activities(self):
        activities = self._action_schedule_activities()
        # only the activity a call reports on is marked done once it ends: one logged after
        # the call ended while the wizard was open, or while the call already reports on
        # another, would otherwise be left pending for good
        call = self._get_logged_call()
        if not (call and call._is_call_ongoing() and call.activity_id == activities[:1]):
            activities.action_done()

    def _action_schedule_activities(self):
        activities = super()._action_schedule_activities()
        # a personal activity is on no document: the call has no chatter to show up in
        if self.res_model and (call := self._get_logged_call()):
            call._link_to_logged_activity(activities[:1], self._get_partner_from_target())
        return activities

    # ------------------------------------------------------------
    # CALL LOGGING API
    # ------------------------------------------------------------

    @api.model
    def _get_log_default_record(self, model_name, domain):
        """ The record of ``model_name`` the wizard pre-selects: the first one its list
        ranks, the user logging the call aside. A call held with nobody known ranks no
        one, so its list starts on an unrelated record: pre-select nothing instead. """
        model = self.env[model_name]
        # a model without the mixin ranks nothing and has no partner to set the user aside by
        is_call_log_model = isinstance(model, self.pool['discuss.call.log.mixin'])
        is_ranked = is_call_log_model and 'log_channel_partner_ids' in self.env.context
        if not self._get_log_filter_contact() and not is_ranked:
            return model
        domain = Domain(domain or Domain.TRUE)
        if is_call_log_model:
            domain &= ~model._get_call_log_partner_domain(self.env.user.partner_id)
        offered = model.name_search('', domain, limit=1)
        return model.browse(offered[0][0]) if offered else model

    @api.model
    def _get_log_filter_contact(self):
        """ The contact the wizard restricts its lists to, void when they are to be left
        whole: a call held with several contacts merely ranks theirs first
        (see `discuss.call.log.mixin.name_search`). """
        if 'log_channel_partner_ids' in self.env.context:
            return self.env['res.partner']
        return self.env['res.partner'].browse(self.env.context.get('log_contact_id'))

    def _get_logged_call(self):
        """ The call being logged, which a module with a call of its own overrides. Such
        a call answers `_is_call_ongoing` and `_link_to_logged_activity`, and holds the
        `activity_id` it reports on. """
        self.ensure_one()
        return self.call_history_id

    def _get_logged_call_depends(self):
        """ The dependencies of what is computed from the logged call, which a module
        overriding `_get_logged_call` extends. """
        return ('call_history_id.end_dt',)

    def _get_partner_from_target(self):
        """ The partner of the record the activity is logged on, void when it has none. """
        record = self._get_applied_on_records()
        if self.res_model == 'res.partner':
            return record
        if 'partner_id' in record._fields:
            return record.partner_id
        return self.env['res.partner']

    def _get_res_model_fields(self):
        """ The field holding the record of each record type, which a module adding one
        of its own overrides. """
        return {'res.partner': 'contact_id'}

    def _get_res_model_from_selection(self, selection_key):
        """ The model a record type applies on, which a module whose record type is not
        a model of its own overrides. """
        return selection_key

    @api.model
    def _is_logging_call(self):
        """ Whether a call is being logged on a document, as opposed to an activity being
        scheduled on a record already known. """
        context = self.env.context
        return bool(context.get('log_contact_id')) or 'log_channel_partner_ids' in context

    def _selection_res_model(self):
        """ The record types the wizard lists, which a module adding one of its own
        overrides. """
        return [('res.partner', self.env._("Contact"))]
