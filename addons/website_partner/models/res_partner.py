# -*- coding: utf-8 -*-

from odoo import api, fields, models
from odoo.tools.translate import html_translate


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'website.seo.metadata']

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

    def _compute_website_url(self):
        super()._compute_website_url()
        for partner in self:
            if partner.id:
                partner.website_url = "/partners/%s" % self.env['ir.http']._slug(partner)

    def _get_contact_opportunities_domain(self):
        all_partners = self._fetch_children_partners_for_hierarchy().ids
        return ['|', ('partner_assigned_id', 'in', all_partners), ('partner_id', 'in', all_partners)]

    def _compute_opportunity_count(self):
        if not self.ids or not self.env.user.has_group('sales_team.group_sale_salesman'):
            return super()._compute_opportunity_count()

        self.opportunity_count = 0
        opportunity_data = self.env['crm.lead'].with_context(active_test=False)._read_group(
            self._get_contact_opportunities_domain(),
            ['partner_assigned_id', 'partner_id'], ['__count']
        )
        current_pids = set(self._ids)
        for assign_partner, partner, count in opportunity_data:
            # this variable is used to keep the track of the partner
            seen_partners = set()
            while partner or assign_partner:
                if assign_partner and assign_partner.id in current_pids and assign_partner not in seen_partners:
                    assign_partner.opportunity_count += count
                    seen_partners.add(assign_partner)
                if partner and partner.id in current_pids and partner not in seen_partners:
                    partner.opportunity_count += count
                    seen_partners.add(partner)
                assign_partner = assign_partner.parent_id
                partner = partner.parent_id
