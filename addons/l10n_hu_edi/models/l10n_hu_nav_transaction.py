# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class L10nHuNavTransaction(models.Model):
    _name = "l10n_hu.upload_transaction"
    _description = "Hungarian TAX Authority Upload Transactions"
    _order = "query_time"
    _rec_name = "transaction_code"
    _rec_names_search = ["token_code", "request_code", "transaction_code"]

    invoice_id = fields.Many2one(
        "account.move", string="Invoice", required=True, index="btree_not_null", ondelete="cascade"
    )
    token_code = fields.Char("Token Code", index="trigram")
    request_code = fields.Char("Request Code", required=True, index="trigram")
    user = fields.Char("NAV Username", required=True)
    version = fields.Char("Protocol Version", required=True)
    production_mode = fields.Boolean("Production System")

    query_time = fields.Datetime("Upload Time", required=True, default=fields.Datetime.now, index=True)
    transaction_code = fields.Char("Transaction Code", required=True, index="trigram")

    reply_status = fields.Selection(
        [
            ("sent", "Uploaded - waiting for reply"),
            ("ok", "OK"),
            ("error", "Error"),
            ("ok_w", "OK - Warning"),
            ("ok_i", "OK - Info"),
        ],
        string="Reply Code",
        required=True,
        default="sent",
        index="btree_not_null",
    )
    reply_message = fields.Html("Reply Message")
    reply_time = fields.Datetime("Reply Time")
