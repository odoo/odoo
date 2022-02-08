# -*- coding: utf-8 -*-


from odoo import fields, models


class ResPartnerIap(models.Model):
    """Technical model which stores the response returned by IAP.

    The goal of this model is to not enrich 2 times the same company. We do it in a
    separate model to not add heavy field (iap_enrich_info) on the <res.partner>
    model.

    We also save the requested domain, so whatever the values are on the <res.partner>,
    we will always retrieve the already enriched <res.partner> and the corresponding
    IAP information.
    """

    _name = 'res.partner.iap'
    _description = 'Partner IAP'

    partner_id = fields.Many2one('res.partner', string='Partner', help='Corresponding partner',
                                 ondelete='cascade', required=True)
    iap_search_domain = fields.Char('Search Domain / Email', help='Domain used to find the company')
    iap_enrich_info = fields.Text('IAP Enrich Info', help='IAP response stored as a JSON string', readonly=True)

    _sql_constraints = [('unique_partner_id', 'UNIQUE(partner_id)', 'Only one partner IAP is allowed for one partner')]
