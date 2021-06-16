# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import random
from ast import literal_eval
from datetime import timedelta

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from odoo.osv import expression


class MassMailingTestingCampaign(models.Model):
    """
    This models allows to manage A/B Testing Campaigns
    """
    _name = 'mailing.ab.testing'
    _description = "A/B Testing Campaign"
    _inherit = ['mail.thread', 'mail.activity.mixin', 'mail.render.mixin']

    def _get_default_mailing_domain(self):
        mailing_domain = []
        if hasattr(self.env[self.mailing_model_name], '_mailing_get_default_domain'):
            mailing_domain = self.env[self.mailing_model_name]._mailing_get_default_domain(self)

        if self.mailing_type == 'mail' and 'is_blacklisted' in self.env[self.mailing_model_name]._fields:
            mailing_domain = expression.AND([[('is_blacklisted', '=', False)], mailing_domain])

        return mailing_domain

    def _parse_mailing_domain(self):
        self.ensure_one()
        try:
            mailing_domain = literal_eval(self.mailing_domain)
        except Exception:
            mailing_domain = [('id', 'in', [])]
        return mailing_domain

    name = fields.Char('Title', required=True)
    active = fields.Boolean(default=True, tracking=True)
    mailing_ids = fields.One2many('mailing.mailing', 'testing_mailing_id', string='Mailings')
    nbr_mailing_ids = fields.Integer('Mailings #', compute='_compute_nbr_mailing_ids')
    mailing_count = fields.Integer('Number of Testing Mailings', compute="_compute_mailing_count")
    mailing_type = fields.Selection([('mail', 'Email')], string="Mailing Type", default="mail", required=True)
    mailing_model_real = fields.Char(string='Recipients Real Model', compute='_compute_mailing_model_real')
    mailing_model_id = fields.Many2one('ir.model', string='Recipients Model', ondelete='cascade',
        required=True, domain=[('is_mailing_enabled', '=', True)],
        default=lambda self: self.env.ref('mass_mailing.model_mailing_list').id)
    mailing_model_name = fields.Char(
        string='Recipients Model Name', related='mailing_model_id.model',
        readonly=True, related_sudo=True)
    mailing_domain = fields.Char('Domain', compute='_compute_mailing_domain', readonly=False, store=True)
    contact_list_ids = fields.Many2many('mailing.list', 'mail_testing_mass_mailing_list_rel', string="Mailing Lists")
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, required=True)
    testing_mode = fields.Selection([('manual', 'Manual'), ('based_on', 'Based On')], string='Testing Mode',
        default='based_on', required=True)
    based_on = fields.Selection([
        ('opened', 'Most Opened'),
        ('clicked', 'Most Clicks'),
        ('replied', 'Most Replied')], string='Based on', default='opened')
    sample_size = fields.Selection([
        ('5', '5%'),
        ('10', '10%'),
        ('15', '15%'),
        ('20', '20%'),
        ('25', '25%'),
        ('40', '40%')], default='25', required=True,
        help="Total percentage of the recipients that will be used to test the mailings.")
    campaign_id = fields.Many2one('utm.campaign', string='UTM Campaign', index=True)
    mailing_trace_ids = fields.One2many('mailing.trace', 'testing_campaign_id', string='Emails Statistics')

    duration_type = fields.Selection([
        ('min', 'Minutes'),
        ('hours', 'Hours'),
        ('days', 'Days')], string="Duration Type", default='days')
    duration = fields.Float("After", default="1")
    state = fields.Selection([('new', 'New'), ('in_progress', 'In Progress'), ('done', 'Done')],
        string='Status', default='new', group_expand='_group_expand_states', required=True)
    tag_ids = fields.Many2many('mailing.ab.testing.tag', 'mailing_ab_testing_tag_rel',
        'mailing_ab_testing_tag_id', 'tag_id', string='Tags')
    total_recipients = fields.Integer('Total Recipients', compute='_compute_total_recipients')

    @api.constrains('mailing_model_id', 'mailing_domain', 'sample_size')
    def _constrains_recipients_nbr(self):
        for mailing in self:
            contact_nbr = self.env[mailing.mailing_model_real].search_count(mailing._parse_mailing_domain())
            if contact_nbr * int(mailing.sample_size) / 200 < 1:
                raise ValidationError(_("There are not enough recipients to test your mailing."))

    @api.model
    def create(self, vals):
        vals['campaign_id'] = self.env['utm.campaign'].create({
            'name': 'Mass Mailing A/B Testing: %s' % vals['name']
        }).id
        return super().create(vals)

    @api.depends('mailing_ids')
    def _compute_nbr_mailing_ids(self):
        for mailing in self:
            mailing.nbr_mailing_ids = len(mailing.mailing_ids)

    @api.depends('mailing_model_id', 'mailing_domain')
    def _compute_total_recipients(self):
        for mailing in self:
            mailing.total_recipients = self.env[mailing.mailing_model_real].search_count(mailing._parse_mailing_domain())

    @api.depends('mailing_model_id')
    def _compute_mailing_model_real(self):
        for mailing in self:
            mailing.mailing_model_real = (mailing.mailing_model_name != 'mailing.list') and mailing.mailing_model_name or 'mailing.contact'

    @api.depends('mailing_model_name', 'contact_list_ids')
    def _compute_mailing_domain(self):
        for mailing in self:
            if not mailing.mailing_model_name:
                mailing.mailing_domain = ''
            else:
                mailing.mailing_domain = repr(mailing._get_default_mailing_domain())

    @api.depends('mailing_model_real')
    def _compute_render_model(self):
        for mailing in self:
            mailing.render_model = mailing.mailing_model_real

    @api.depends('mailing_ids')
    def _compute_mailing_count(self):
        mailing_data = self.env['mailing.mailing'].read_group(
            [('testing_mailing_id', 'in', self.ids)],
            ['testing_mailing_id'], ['testing_mailing_id'])
        count_data = dict(
            (item['testing_mailing_id'][0], item['testing_mailing_id_count']) for item in mailing_data
        )
        for testing_mailing in self:
            testing_mailing.mailing_count = count_data.get(testing_mailing.id, 0)

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    def action_add_mailing(self):
        return {
            'name': 'Mailing Test',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mailing.mailing',
            'context': dict(self._context, **{
                'default_mailing_model_id': self.mailing_model_id.id,
                'default_mailing_domain': self.mailing_domain,
                'default_contact_list_ids': self.contact_list_ids.ids,
                'default_testing_mailing_id': self.id,
                'default_mailing_type': self.mailing_type,
            }),
        }

    def action_send_mailings(self, mailings=False):
        self.ensure_one()
        cron = self.env.ref('mass_mailing.ir_cron_mass_mailing_ab_testing').sudo()
        if not mailings:
            mailings = self.mailing_ids.filtered(lambda m: m.state == 'draft')
        for mailing in mailings:
            recipients = self._get_recipients(mailing.contact_ab_pc)
            if recipients:
                mailing.campaign_id = self.campaign_id
                mailing.action_send_mail(recipients)
            else:
                raise ValidationError(_("There are not enough recipients to send the testing mailings. Increase the sample size or the number of recipients"))
        self.write({'state': 'in_progress'})
        at = mailing.sent_date + timedelta(hours=self._get_duration_hours())
        if not cron.lastcall or at > cron.lastcall:
            cron._trigger(at=at)

    def action_send_winner_mailing(self):
        self.ensure_one()
        if self.testing_mode == 'based_on' and self.mailing_ids:
            sorted_by = self._get_sort_by_field()
            selected_mailing = self.mailing_ids.filtered(lambda m: m.state == 'done').sorted(sorted_by, reverse=True)[0]
            final_mailing = selected_mailing.copy()
            old_version_name = selected_mailing.version_id.name if selected_mailing.version_id else _("Version")
            version_name = _("%s - Final", old_version_name)
            version_id = self.env['mailing.mailing.version']._search_create_version_id(version_name)
            final_mailing.write({
                'is_winner': True,
                'version_id': version_id.id,
            })
            final_mailing.action_send_mail(self._get_remaining_recipients())
            self.write({'state': 'done'})

    def _get_recipients(self, percentage_used):
        mailing_domain = self._parse_mailing_domain()
        res_ids = self.env[self.mailing_model_real].search(mailing_domain).ids

        contact_nbr = len(res_ids)
        topick = int(contact_nbr * percentage_used)

        if self.campaign_id:
            already_mailed = self.campaign_id._get_mailing_recipients()[self.campaign_id.id]
        else:
            already_mailed = set([])

        remaining = set(res_ids).difference(already_mailed)
        if topick > len(remaining):
            topick = len(remaining)
        res_ids = random.sample(remaining, topick)
        return res_ids

    def _get_remaining_recipients(self):
        mailing_domain = self._parse_mailing_domain()
        res_ids = set(self.env[self.mailing_model_real].search(mailing_domain).ids)
        for mailing in self.mailing_ids:
            already_mailed = set([trace.res_id for trace in mailing.mailing_trace_ids])
            res_ids = res_ids.difference(already_mailed)
        return list(res_ids)

    def _get_duration_hours(self):
        if self.duration_type == 'min':
            duration_hours = self.duration / 60.0
        elif self.duration_type == 'days':
            duration_hours = self.duration * 24
        else:
            duration_hours = self.duration

        return duration_hours

    def _get_sort_by_field(self):
        return self.based_on

    @api.model
    def _process_mass_mailing_ab_testing(self):
        testing_mailings = self.search([('state', '=', 'in_progress'), ('testing_mode', '=', 'based_on')])
        for test_mailing in testing_mailings:
            last_mailing_sent = test_mailing.mailing_ids.sorted('sent_date', reverse=True)[0]

            duration_hours = test_mailing._get_duration_hours()
            if last_mailing_sent.sent_date <= fields.Datetime.now() - timedelta(hours=duration_hours):
                test_mailing.action_send_winner_mailing()
