# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentAcquirer(models.Model):

    _inherit = 'payment.acquirer'

    @api.model
    def _get_compatible_acquirers(self, *_args, **kwargs):
        """ Select and return the acquirers matching the criteria.

        In addition to the base criteria, the website must either not be set or be the same as the
        one provided in the kwargs.

        :param list _args: Base data. This parameter is not used here
        :param dict kwargs: Optional data. Processed keys: website_id
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        acquirers = super()._get_compatible_acquirers(*_args, **kwargs)
        if 'website_id' in kwargs:
            return acquirers.filtered(
                lambda a: not a.website_id or a.website_id.id == kwargs['website_id']
            )
        return acquirers
