# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, api, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    branch_code = fields.Char("Branch Code", default='000', compute='_compute_branch_code', store=True)
    l10n_ph_entity_type = fields.Selection([
            ('individual', 'Individual'),
            ('corporation', 'Corporation'),
        ],
        string='Type of Entity',
        help='Philippines: Defines the type of entity.'
    )
    first_name = fields.Char("First Name")
    middle_name = fields.Char("Middle Name")
    last_name = fields.Char("Last Name")

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ['branch_code']

    @api.depends('vat', 'country_id')
    def _compute_branch_code(self):
        for partner in self:
            branch_code = '000'
            if partner.country_id.code == 'PH' and partner.vat:
                match = partner._check_vat_ph_re.match(partner.vat)
                branch_code = match and match.group(1) and match.group(1)[1:] or branch_code
            partner.branch_code = branch_code

    @api.depends('vat', 'commercial_partner_id', 'country_code', 'l10n_ph_entity_type')
    def _compute_is_company(self):
        ph_partners = self.filtered(lambda partner: partner.country_code == 'PH' and partner.l10n_ph_entity_type)
        for partner in ph_partners:
            partner.is_company = partner.l10n_ph_entity_type == 'corporation'
        super(ResPartner, self - ph_partners)._compute_is_company()

    @api.onchange('l10n_ph_entity_type')
    def _onchange_entity_type(self):
        if self.l10n_ph_entity_type == 'corporation':
            self.first_name = False
            self.middle_name = False
            self.last_name = False
