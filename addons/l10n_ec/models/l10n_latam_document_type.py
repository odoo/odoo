# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class L10nLatamDocumentType(models.Model):
    _inherit = 'l10n_latam.document.type'
    
    _EC_TYPE = [
        ('out_invoice', 'Customer Document'),
        ('in_invoice', 'Supplier Document'),
        ('out_refund', 'Customer Refund'),
        ('in_refund', 'Supplier Refund'),
        ('out_waybill', 'Issued Waybill'),
        ('out_withhold', 'Customer Withhold'),
        ('in_withhold', 'Supplier Withhold'),
        ('hr_advance', 'Employee Advance'),
        ('other', 'Others'),
    ]

    _EC_AUTHORIZATION = [
        ('none', 'None'),
        ('own', 'Issued by my company'),
        ('third', 'Issued by Third Parties')
    ]

    l10n_ec_type = fields.Selection(
        _EC_TYPE, 
        string='Ecuadorian Type',
        help='Indicates the aplicability of the document',
        )
    l10n_ec_require_vat = fields.Boolean(
        string='Require Vat Number', 
        track_visibility='onchange',
        help='Force the registration of customer vat number on invoice validation',
        )
    l10n_ec_authorization = fields.Selection(
        _EC_AUTHORIZATION,
        default='none',
        string='Authorization',
        help='Ecuadorian tax authority requires an authorization for certain documents',
        )
