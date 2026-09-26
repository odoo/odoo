# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class L10nPhQrph(http.Controller):

    @http.route('/l10n_ph/qrph/webhook', type='http', auth='public', methods=['POST'], csrf=False, save_session=False)
    def l10n_ph_qrph_webhook(self):
        """ Settle what a QRPH code was minted for, as soon as Maya reports the code paid.

        Maya signs nothing it sends here, so the notification is taken as no more than a hint that
        a payment is worth a look: what settles anything is the status we then ask Maya for
        ourselves, with the key of the bank account the code was minted with. A caller making this
        up therefore gets nothing out of it but a status request for a code that already exists.

        :return: an empty body, to acknowledge the notification
        :rtype: str
        """
        maya_payment_id = (request.get_json_data() or {}).get('id')
        if not maya_payment_id:
            return ''

        # sudo: Maya is nobody in Odoo, and the codes are readable by accountants only.
        transaction = request.env['l10n_ph.qrph.transaction'].sudo().search([
            ('maya_payment_id', '=', maya_payment_id),
        ], limit=1)
        if not transaction:
            # A code minted by another database sharing the Maya account, or one long vacuumed.
            return ''

        # Letting a failure to reach Maya bubble up leaves the notification unanswered, which is
        # what gets Maya to send it again rather than us dropping a payment on a network blip.
        if transaction._get_paid_transaction():
            _logger.info("QRPH: Maya payment %s reported paid, settling %s %s.",
                         maya_payment_id, transaction.model, transaction.model_id)
            transaction._l10n_ph_qrph_settle()
        return ''
