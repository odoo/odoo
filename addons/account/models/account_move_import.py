import logging
from contextlib import contextmanager

from odoo import api, models
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.libs.debug_log import DebugLog

_logger = logging.getLogger(__name__)

_debug = DebugLog(__name__)


class AccountMove(models.Model):
    _inherit = "account.move"

    @_debug.perf.timed
    def _extend_with_attachments(self, files_data, new=False):
        existing_lines = self.invoice_line_ids
        res = super()._extend_with_attachments(files_data, new)
        _debug.pipeline(
            "import_new",
            move=self,
            extended=res,
            lines=len(self.invoice_line_ids - existing_lines),
        )

        if new_lines := (self.invoice_line_ids - existing_lines):
            new_lines.is_imported = True
            if not existing_lines:
                try:
                    self.with_context(
                        default_move_type=self.move_type
                    )._link_bill_origin_to_purchase_orders(timeout=4)
                except UserError, ValueError:
                    _logger.exception("Failed to link bill to purchase order")

        if new and res:
            self._portal_get_or_create_token()
            self.flush_recordset(["access_token"])
            try:
                attachments = set(
                    self.attachment_ids
                    + self._from_files_data(
                        files_data + self._unwrap_attachments(files_data)
                    )
                )
                self.journal_id._notify_invoice_subscribers(
                    invoice=self,
                    mail_params={
                        "attachment_ids": [
                            Command.create(
                                {
                                    "name": f"MAIL_{attachment['name']}",
                                    "mimetype": attachment["mimetype"],
                                    "raw": attachment["raw"],
                                }
                            )
                            for attachment in attachments
                        ]
                    },
                )
            except Exception:
                _logger.exception(
                    "Failed to notify invoice subscribers after EDI import."
                )

        self._post_process_link_to_purchase_order(self)

        return res

    @contextmanager
    def _get_edi_creation(self):
        container = {"records": self}
        with (
            self._check_balanced(container),
            self._disable_discount_precision(),
            self._sync_dynamic_lines(container),
        ):
            move = self or self.create({})
            container["records"] = move
            yield move

    @contextmanager
    def _disable_discount_precision(self):
        with self._disable_recursion("ignore_discount_precision"):
            yield

    def _reason_cannot_decode_has_invoice_lines(self):
        if self.invoice_line_ids:
            return self.env._("The invoice already contains lines.")
        return None

    @api.model
    def _post_process_link_to_purchase_order(self, invoice):
        pass

    @_debug.perf.timed
    def _prepare_edi_vals_to_export(self):
        self.check_singleton()

        res = {
            "record": self,
            "balance_multiplicator": -1 if self.is_inbound() else 1,
            "invoice_line_vals_list": [],
        }

        for index, line in enumerate(
            self.invoice_line_ids.filtered(lambda line: line.display_type == "product"),
            start=1,
        ):
            line_vals = line._prepare_edi_vals_to_export()
            line_vals["index"] = index
            res["invoice_line_vals_list"].append(line_vals)

        res.update(
            {
                "total_price_subtotal_before_discount": sum(
                    x["price_subtotal_before_discount"]
                    for x in res["invoice_line_vals_list"]
                ),
                "total_price_discount": sum(
                    x["price_discount"] for x in res["invoice_line_vals_list"]
                ),
            }
        )

        return res
