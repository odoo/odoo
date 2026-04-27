# -*- coding: utf-8 -*-

from odoo import fields, models, api, _

import logging

_logger = logging.getLogger(__name__)

ADDRESS_FIELDS = ('street', 'street2', 'city', 'state_id', 'zip', 'country_id')


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'account.avatax.unique.code']

    avalara_partner_code = fields.Char(
        string='Avalara Partner Code',
        help="Customer Code set in Avalara for this partner.",
    )
    avalara_exemption_id = fields.Many2one(
        comodel_name='avatax.exemption',
        company_dependent=True,
        domain="['|', ('valid_country_ids', 'in', country_id), ('valid_country_ids', '=', False)]",
    )
    # field used to hide the address validation button when the partner is not in the US or Canada
    avalara_show_address_validation = fields.Boolean(
        compute='_compute_avalara_show_address_validation',
        store=False,
        string='Avalara Show Address Validation',
    )

    @api.depends('country_id')
    def _compute_avalara_show_address_validation(self):
        for partner in self:
            company = partner.company_id or self.env.company
            partner.avalara_show_address_validation = company.avalara_address_validation and partner.street and (not partner.country_id or partner.fiscal_country_codes in ('US', 'CA'))

    def _get_avatax_description(self):
        return 'Contact'

    def action_open_validation_wizard(self):
        self.ensure_one()
        return {
            'name': _('Validate address of %s', self.display_name),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'avatax.validate.address',
            'target': 'new',
            'context': {'default_partner_id': self.id},
        }
