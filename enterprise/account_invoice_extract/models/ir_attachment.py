# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def register_as_main_attachment(self, force=True):
        """Add the automatic scanning of attachments when registered as main.
           To avoid double scanning after message_post, we check that the automatic scanning is only made the first time.
        """
        super().register_as_main_attachment(force=force)

        move_attachments = self.filtered(lambda a: a.res_model == "account.move")
        for move in self.env["account.move"].browse(move_attachments.mapped("res_id")):
            if move._needs_auto_extract():
                move._send_batch_for_digitization()
