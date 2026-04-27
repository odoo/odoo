# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _post(self, soft=True):
        posted = super()._post(soft=soft)
        self.filtered(lambda am: am.sudo().pos_order_ids).edi_document_ids.filtered(
                lambda d: d.state == 'to_send')._process_documents_web_services(job_count=1)
        return posted
