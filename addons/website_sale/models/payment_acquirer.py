# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PaymentAcquirer(models.Model):

    _inherit = 'payment.acquirer'

    @api.model
    def _get_compatible_acquirers(self, *args, website_id=None, **kwargs):
        """ Override of payment to only return acquirers matching website-specific criteria.

        In addition to the base criteria, the website must either not be set or be the same as the
        one provided in the kwargs.

        :param int website_id: The provided website, as a `website` id
        :return: The compatible acquirers
        :rtype: recordset of `payment.acquirer`
        """
        acquirers = super()._get_compatible_acquirers(*args, website_id=website_id, **kwargs)
        if website_id:
            acquirers = acquirers.filtered(
                lambda a: not a.website_id or a.website_id.id == website_id
            )
        return acquirers
