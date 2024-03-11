# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailActivityType(models.Model):
    """ Activity Types are used to categorize activities. Each type is a different
    kind of activity e.g. call, mail, meeting. An activity can be generic i.e.
    available for all models using activities; or specific to a model in which
    case res_model field should be used. """
    _name = 'mail.activity.type'
    _description = 'Activity Type'
    _rec_name = 'name'
    _order = 'sequence, id'

    def _get_model_selection(self):
        return [
            (model.model, model.name)
            for model in self.env['ir.model'].sudo().search(
                ['&', ('is_mail_thread', '=', True), ('transient', '=', False)])
        ]

    name = fields.Char('Name', required=True, translate=True)
    summary = fields.Char('Default Summary', translate=True)
    sequence = fields.Integer('Sequence', default=10)
    active = fields.Boolean(default=True)
    create_uid = fields.Many2one('res.users', index=True)
    delay_count = fields.Integer(
        'Schedule', default=0,
        help='Number of days/week/month before executing the action. It allows to plan the action deadline.')
    delay_unit = fields.Selection([
        ('days', 'days'),
        ('weeks', 'weeks'),
        ('months', 'months')], string="Delay units", help="Unit of delay", required=True, default='days')
    delay_label = fields.Char(compute='_compute_delay_label')
    delay_from = fields.Selection([
        ('current_date', 'after completion date'),
        ('previous_activity', 'after previous activity deadline')], string="Delay Type", help="Type of delay", required=True, default='previous_activity')
    icon = fields.Char('Icon', help="Font awesome icon e.g. fa-tasks")
    decoration_type = fields.Selection([
        ('warning', 'Alert'),
        ('danger', 'Error')], string="Decoration Type",
        help="Change the background color of the related activities of this type.")
    res_model = fields.Selection(selection=_get_model_selection, string="Model",
        help='Specify a model if the activity should be specific to a model'
             ' and not available when managing activities for other models.')
    triggered_next_type_id = fields.Many2one(
        'mail.activity.type', string='Trigger', compute='_compute_triggered_next_type_id',
        inverse='_inverse_triggered_next_type_id', store=True, readonly=False,
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]", ondelete='restrict',
        help="Automatically schedule this activity once the current one is marked as done.")
    chaining_type = fields.Selection([
        ('suggest', 'Suggest Next Activity'), ('trigger', 'Trigger Next Activity')
    ], string="Chaining Type", required=True, default="suggest")
    suggested_next_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'activity_id', 'recommended_id', string='Suggest',
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]",
        compute='_compute_suggested_next_type_ids', inverse='_inverse_suggested_next_type_ids', store=True, readonly=False,
        help="Suggest these activities once the current one is marked as done.")
    previous_type_ids = fields.Many2many(
        'mail.activity.type', 'mail_activity_rel', 'recommended_id', 'activity_id',
        domain="['|', ('res_model', '=', False), ('res_model', '=', res_model)]",
        string='Preceding Activities')
    category = fields.Selection([
        ('default', 'None'),
        ('upload_file', 'Upload Document'),
        ('phonecall', 'Phonecall')
    ], default='default', string='Action',
        help='Actions may trigger specific behavior like opening calendar view or automatically mark as done when a document is uploaded')
    mail_template_ids = fields.Many2many('mail.template', string='Email templates')
    default_user_id = fields.Many2one("res.users", string="Default User")
    default_note = fields.Html(string="Default Note", translate=True)

    #Fields for display purpose only
    initial_res_model = fields.Selection(selection=_get_model_selection, string='Initial model', compute="_compute_initial_res_model", store=False,
            help='Technical field to keep track of the model at the start of editing to support UX related behaviour')
    res_model_change = fields.Boolean(string="Model has change", default=False, store=False)

    @api.onchange('res_model')
    def _onchange_res_model(self):
        self.mail_template_ids = self.sudo().mail_template_ids.filtered(lambda template: template.model_id.model == self.res_model)
        self.res_model_change = self.initial_res_model and self.initial_res_model != self.res_model

    def _compute_initial_res_model(self):
        for activity_type in self:
            activity_type.initial_res_model = activity_type.res_model

    @api.depends('delay_unit', 'delay_count')
    def _compute_delay_label(self):
        selection_description_values = {
            e[0]: e[1] for e in self._fields['delay_unit']._description_selection(self.env)}
        for activity_type in self:
            unit = selection_description_values[activity_type.delay_unit]
            activity_type.delay_label = '%s %s' % (activity_type.delay_count, unit)

    @api.depends('chaining_type')
    def _compute_suggested_next_type_ids(self):
        """suggested_next_type_ids and triggered_next_type_id should be mutually exclusive"""
        for activity_type in self:
            if activity_type.chaining_type == 'trigger':
                activity_type.suggested_next_type_ids = False

    def _inverse_suggested_next_type_ids(self):
        for activity_type in self:
            if activity_type.suggested_next_type_ids:
                activity_type.chaining_type = 'suggest'

    @api.depends('chaining_type')
    def _compute_triggered_next_type_id(self):
        """suggested_next_type_ids and triggered_next_type_id should be mutually exclusive"""
        for activity_type in self:
            if activity_type.chaining_type == 'suggest':
                activity_type.triggered_next_type_id = False

    def _inverse_triggered_next_type_id(self):
        for activity_type in self:
            if activity_type.triggered_next_type_id:
                activity_type.chaining_type = 'trigger'
            else:
                activity_type.chaining_type = 'suggest'
