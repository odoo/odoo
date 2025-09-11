# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata']

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

    website_description = fields.Html('Website Partner Full Description', strip_style=True, sanitize_overridable=True, translate=html_translate)
    website_short_description = fields.Text('Website Partner Short Description', translate=True)

    # customer implementation
    assigned_partner_id = fields.Many2one(
        'res.partner', 'Implemented by', index='btree_not_null',
    )
    implemented_partner_ids = fields.One2many(
        'res.partner', 'assigned_partner_id',
        string='Implementation References',
    )
    implemented_partner_count = fields.Integer(compute='_compute_implemented_partner_count', store=True)

    partner_weight = fields.Integer(
        'Level Weight', compute='_compute_partner_weight',
        readonly=False, store=True, tracking=True,
        help="This should be a numerical value greater than 0 which will decide the contention for this partner to take this lead/opportunity.")
    grade_sequence = fields.Integer(related='grade_id.sequence', readonly=True, store=True)

    activation = fields.Many2one('res.partner.activation', 'Activation', index='btree_not_null', tracking=True)
    date_partnership = fields.Date('Partnership Date')
    date_review = fields.Date('Latest Review')
    date_review_next = fields.Date('Next Review')

    @api.depends('implemented_partner_ids.is_published', 'implemented_partner_ids.active')
    def _compute_implemented_partner_count(self):
        rg_result = self.env['res.partner']._read_group(
            [('assigned_partner_id', 'in', self.ids),
             ('is_published', '=', True)],
            ['assigned_partner_id'],
            ['__count'],
        )
        rg_data = {assigned_partner.id: count for assigned_partner, count in rg_result}
        for partner in self:
            partner.implemented_partner_count = rg_data.get(partner.id, 0)

    @api.depends('grade_id.partner_weight')
    def _compute_partner_weight(self):
        for partner in self:
            partner.partner_weight = partner.grade_id.partner_weight if partner.grade_id else 0

    def _compute_website_url(self):
        super()._compute_website_url()
        for partner in self:
            if partner.id:
                partner.website_url = "/partners/%s" % self.env['ir.http']._slug(partner)
