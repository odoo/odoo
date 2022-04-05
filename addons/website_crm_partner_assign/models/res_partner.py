# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression
from odoo.addons.http_routing.models.ir_http import slug


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _order = 'sequence'
    _inherit = ['website.published.mixin']
    _description = 'Partner Grade'

    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', default=lambda *args: 1)
    name = fields.Char('Level Name', translate=True)
    partner_weight = fields.Integer('Level Weight', default=1,
        help="Gives the probability to assign a lead to this partner. (0 means no assignment.)")

    def _compute_website_url(self):
        super(ResPartnerGrade, self)._compute_website_url()
        for grade in self:
            grade.website_url = "/partners/grade/%s" % (slug(grade))

    def _default_is_published(self):
        return True


class ResPartnerActivation(models.Model):
    _name = 'res.partner.activation'
    _order = 'sequence'
    _description = 'Partner Activation'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def default_get(self, fields_list):
        default_vals = super().default_get(fields_list)
        if self.env.context.get('partner_set_default_grade_activation'):
            # sets the lowest grade and activation if no default values given, mainly useful while
            # creating assigned partner on the fly (to make it visible in same m2o again)
            if 'grade_id' in fields_list and not default_vals.get('grade_id'):
                default_vals['grade_id'] = self.env['res.partner.grade'].search([], order='sequence', limit=1).id
            if 'activation' in fields_list and not default_vals.get('activation'):
                default_vals['activation'] = self.env['res.partner.activation'].search([], order='sequence', limit=1).id
        return default_vals

    partner_weight = fields.Integer(
        'Level Weight', compute='_compute_partner_weight',
        readonly=False, store=True, tracking=True,
        help="This should be a numerical value greater than 0 which will decide the contention for this partner to take this lead/opportunity.")
    grade_id = fields.Many2one('res.partner.grade', 'Partner Level', tracking=True)
    grade_sequence = fields.Integer(related='grade_id.sequence', readonly=True, store=True)
    activation = fields.Many2one('res.partner.activation', 'Activation', index='btree_not_null', tracking=True)
    date_partnership = fields.Date('Partnership Date')
    date_review = fields.Date('Latest Partner Review')
    date_review_next = fields.Date('Next Partner Review')
    # customer implementation
    assigned_partner_id = fields.Many2one(
        'res.partner', 'Implemented by',
    )
    implemented_partner_ids = fields.One2many(
        'res.partner', 'assigned_partner_id',
        string='Implementation References',
    )
    implemented_count = fields.Integer(compute='_compute_implemented_partner_count', store=True)

    @api.depends('implemented_partner_ids', 'implemented_partner_ids.website_published', 'implemented_partner_ids.active')
    def _compute_implemented_partner_count(self):
        for partner in self:
            partner.implemented_count = len(partner.implemented_partner_ids.filtered('website_published'))

    @api.depends('grade_id.partner_weight')
    def _compute_partner_weight(self):
        for partner in self:
            partner.partner_weight = partner.grade_id.partner_weight if partner.grade_id else 0

    def _compute_opportunity_count(self):
        super()._compute_opportunity_count()
        assign_counts = {}
        if self.ids:
            opportunity_data = self.env['crm.lead'].with_context(active_test=False).read_group(
                [('partner_assigned_id', 'in', self.ids)],
                ['partner_assigned_id'], ['partner_assigned_id']
            )
            assign_counts = {datum['partner_assigned_id'][0]: datum['partner_assigned_id_count'] for datum in opportunity_data}
        for partner in self:
            partner.opportunity_count += assign_counts.get(partner.id, 0)

    def action_view_opportunity(self):
        self.ensure_one()  # especially here as we are doing an id, in, IDS domain
        action = super().action_view_opportunity()
        action_domain_origin = action.get('domain')
        action_context_origin = action.get('context') or {}
        action_domain_assign = [('partner_assigned_id', '=', self.id)]
        if not action_domain_origin:
            action['domain'] = action_domain_assign
            return action
        # perform searches independently as having OR with those leaves seems to
        # be counter productive
        Lead = self.env['crm.lead'].with_context(**action_context_origin)
        ids_origin = Lead.search(action_domain_origin).ids
        ids_new = Lead.search(action_domain_assign).ids
        action['domain'] = [('id', 'in', sorted(list(set(ids_origin) | set(ids_new))))]
        return action
