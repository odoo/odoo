# Part of Odoo. See LICENSE file for full copyright and licensing details.
import random
import datetime
import logging
from dateutil.relativedelta import relativedelta

from odoo import models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class Partner(models.Model):
    _inherit = 'res.partner'

    def _populate(self, size):
        records = super()._populate(size)
        self._populate_membership_state(records)
        return records

    def _populate_membership_state(self, partners):
        """ create invoices for the partners:
            * 10% - unpaid
            * 90% - paid
        """

        membership_1 = self.env['product.product'].create({
            'membership': True,
            'membership_date_from': datetime.date.today() + relativedelta(days=-2),
            'membership_date_to': datetime.date.today() + relativedelta(months=1),
            'name': 'Basic Limited',
            'type': 'service',
            'list_price': 100.00,
        })
        # other companies may have no accounting setup
        partners = partners.filtered(lambda p: not p.company_id or p.company_id == self.env.company)

        count_invoiced = len(partners) * 0.10
        _logger.info("Generating invoices: %s invoiced and %s paid" % (int(count_invoiced), len(partners) - int(count_invoiced)))
        for count, p in enumerate(partners):
            invoice = p.create_membership_invoice(membership_1, 75.0)
            invoice.action_post()
            if (count % 100) == 0:
                _logger.info("Generating invoices: %s/%s" % (count, len(partners)))
            if count <= count_invoiced:
                continue
            try:
                self.env['account.payment.register']\
                    .with_context(active_model='account.move', active_ids=invoice.ids)\
                    .create({
                        'amount': 86.25
                    })\
                    ._create_payments()
            except UserError:
                # there may be some multi-company issues. Just ignore it
                _logger.debug("Error on creating payment. Skip populating this partner", exc_info=True)
