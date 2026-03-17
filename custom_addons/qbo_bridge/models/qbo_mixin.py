"""QboMixin — adds QBO tracking fields to native Odoo models.

These fields are declared on the mixin so each target model only needs
``_inherit = ['<native.model>', 'qbo.mixin']`` to gain QBO tracking.
"""
from odoo import fields, models


class QboMixin(models.AbstractModel):
    """Abstract mixin that adds QBO identity and sync-state fields."""

    _name = "qbo.mixin"
    _description = "QBO sync mixin"

    qbo_id = fields.Char(
        string="QBO ID",
        index=True,
        copy=False,
        help="The entity Id returned by the QuickBooks Online API.",
    )
    qbo_sync_token = fields.Char(
        string="QBO SyncToken",
        copy=False,
        help="QBO optimistic-lock token; must be sent with every update.",
    )
    qbo_realm_id = fields.Many2one(
        "qbo.realm",
        string="QBO realm",
        ondelete="set null",
        copy=False,
        help="The realm this record was last synced from/to.",
    )
    qbo_last_sync = fields.Datetime(
        string="Last QBO sync",
        readonly=True,
        copy=False,
    )


# ── Apply mixin to bridged models ────────────────────────────────────────────

class AccountAccountQbo(models.Model):
    _name = "account.account"
    _inherit = ["account.account", "qbo.mixin"]
    _description = "Account (QBO bridge)"


class ResPartnerQbo(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "qbo.mixin"]
    _description = "Partner (QBO bridge)"


class AccountMoveQbo(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "qbo.mixin"]
    _description = "Journal entry / invoice (QBO bridge)"


class AccountPaymentQbo(models.Model):
    _name = "account.payment"
    _inherit = ["account.payment", "qbo.mixin"]
    _description = "Payment (QBO bridge)"


class ProductTemplateQbo(models.Model):
    _name = "product.template"
    _inherit = ["product.template", "qbo.mixin"]
    _description = "Product (QBO bridge)"
