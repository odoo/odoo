# Copyright (C) 2015 - Today: GRAP (http://www.grap.coop)
# @author: Sylvain LE GAL (https://twitter.com/legalsylvain)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class PosPaymentChangeWizardOldLine(models.TransientModel):
    _name = "pos.payment.change.wizard.old.line"
    _description = "PoS Payment Change Wizard Old Line"

    wizard_id = fields.Many2one(
        comodel_name="pos.payment.change.wizard",
        required=True,
        ondelete="cascade",
    )

    old_payment_method_id = fields.Many2one(
        comodel_name="pos.payment.method",
        string="Payment Method",
        required=True,
        readonly=True,
    )

    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        store=True,
        related="old_payment_method_id.company_id.currency_id",
        string="Company Currency",
        readonly=True,
        help="Utility field to express amount currency",
    )

    amount = fields.Monetary(
        required=True,
        readonly=True,
        default=0.0,
        currency_field="company_currency_id",
    )
