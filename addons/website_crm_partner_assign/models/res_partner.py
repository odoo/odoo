# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.addons.website.models.website import slug


class ResPartnerGrade(models.Model):
    _name = 'res.partner.grade'
    _inherit = ['website.published.mixin']

    website_published = fields.Boolean(default=True)
    sequence = fields.Integer('Sequence')
    active = fields.Boolean('Active', default=lambda *args: 1)
    name = fields.Char('Level Name', translate=True)
    partner_weight = fields.Integer('Level Weight', default=1,
        help="Gives the probability to assign a lead to this partner. (0 means no assignation.)")

    @api.multi
    def _compute_website_url(self):
        super(ResPartnerGrade, self)._compute_website_url()
        for grade in self:
            grade.website_url = "/partners/grade/%s" % (slug(grade))


class ResPartnerActivation(models.Model):
    _name = 'res.partner.activation'
    _order = 'sequence'

    sequence = fields.Integer('Sequence')
    name = fields.Char('Name', required=True)


class ResPartner(models.Model):
    _inherit = "res.partner"

    partner_weight = fields.Integer('Level Weight', default=lambda *args: 0,
        help="Gives the probability to assign a lead to this partner. (0 means no assignation.)")
    grade_id = fields.Many2one('res.partner.grade', 'Level')
    grade_sequence = fields.Integer(related='grade_id.sequence', readonly=True, store=True)
    activation = fields.Many2one('res.partner.activation', 'Activation', index=True)
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

    @api.one
    @api.depends('implemented_partner_ids', 'implemented_partner_ids.website_published', 'implemented_partner_ids.active')
    def _compute_implemented_partner_count(self):
        self.implemented_count = len(self.implemented_partner_ids.filtered('website_published'))

    @api.onchange('grade_id')
    def _onchange_grade_id(self):
        grade = self.grade_id
        self.partner_weight = grade.partner_weight if grade else 0
