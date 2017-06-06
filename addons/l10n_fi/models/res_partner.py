# coding=utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Avoin.Systems 2016

from openerp import api, fields, models, _
from openerp.exceptions import ValidationError


def check_business_id(business_id):
    """
    Validate a Finnish Business ID.
    Specification (in Finnish only):
    https://www.vero.fi/download/Tarkistusmerkin_laskenta/%7BD5780347-547E-4C44-90C1-25F8AD9DA7F8%7D/6508
    """
    if not isinstance(business_id, basestring):
        raise ValidationError(_('Wrong data type passed on as Business ID {}')
                              .format(business_id))

    if len(business_id) == 8:
        business_id = "0" + business_id

    if len(business_id) != 9:
        raise ValidationError(_('Invalid length for Business ID {}')
                              .format(business_id))

    for c in business_id:
        if c not in "0123456789-":
            raise ValidationError(
                _('Business ID {} contains invalid characters').format(
                    business_id))

    split_id = business_id.split('-')
    base = split_id[0]
    check = split_id[1]
    factors = [7, 9, 10, 5, 8, 4, 2]
    if len(base) != 7 or len(check) != 1:
        raise ValidationError(_('Business ID {} is in invalid format')
                              .format(business_id))
    check = int(check)
    product_sum = 0
    for i in range(7):
        product_sum += int(base[i]) * factors[i]
    remainder = product_sum % 11
    if remainder == 0 and check == 0:
        return True
    if remainder == 1 or 11 - remainder != check:
        raise ValidationError(_('Business ID {} is invalid')
                              .format(business_id))
    return True


class ResPartnerFinnish(models.Model):
    _inherit = 'res.partner'

    business_id = fields.Char(
        'Business ID',
        size=9,
        help='Finnish Business ID as defined in '
             'https://www.ytj.fi/en/index/businessid.html',
    )

    # The EDI code format is not standardized, so
    # validation would be quite pointless.
    edi_code = fields.Char(
        'EDI Code',
        size=19,
        help='An EDI identifier of the partner, used to exchange '
             'electronic data, eg. invoices.'
    )

    @api.multi
    @api.constrains('business_id')
    def _check_business_id(self):
        for partner in self:
            if (partner.country_id and partner.country_id.code != 'FI') \
                    or not partner.business_id:
                continue

            check_business_id(partner.business_id)
