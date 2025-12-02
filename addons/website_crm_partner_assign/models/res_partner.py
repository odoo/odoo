# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    @api.model
    def default_get(self, fields):
        default_vals = super().default_get(fields)
        if self.env.context.get('partner_set_default_grade_activation'):
            # sets the lowest grade and activation if no default values given, mainly useful while
            # creating assigned partner on the fly (to make it visible in same m2o again)
            if 'grade_id' in fields and not default_vals.get('grade_id'):
                default_vals['grade_id'] = self.env['res.partner.grade'].search([], order='sequence', limit=1).id
            if 'activation' in fields and not default_vals.get('activation'):
                default_vals['activation'] = self.env['res.partner.activation'].search([], order='sequence', limit=1).id
        return default_vals

    partner_weight = fields.Integer(
        'Level Weight', compute='_compute_partner_weight',
        readonly=False, store=True, tracking=True,
        help="This should be a numerical value greater than 0 which will decide the contention for this partner to take this lead/opportunity.")
    grade_sequence = fields.Integer(related='grade_id.sequence', readonly=True, store=True)
    activation = fields.Many2one('res.partner.activation', 'Activation', index='btree_not_null', tracking=True)
    date_partnership = fields.Date('Partnership Date')
    date_review = fields.Date('Latest Review')
    date_review_next = fields.Date('Next Review')
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

    @api.depends('grade_id.partner_weight')
    def _compute_partner_weight(self):
        for partner in self:
            partner.partner_weight = partner.grade_id.partner_weight if partner.grade_id else 0

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

