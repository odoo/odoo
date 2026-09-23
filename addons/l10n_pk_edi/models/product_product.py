import re

from odoo import fields, models
from ..data.l10n_pk_edi_data import TRANSACTION_TYPE, UOM_CODES

HS_CODE_REGEX = re.compile(r'^\d{4}\.\d{4}$')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    # Fields
    # -------------------------------------------------------------------------

    l10n_pk_edi_hs_code = fields.Char(
        string="HS Code(PK)",
        copy=False,
        help="Standardized code for international shipping and goods declaration.",
    )
    l10n_pk_edi_uom_code = fields.Selection(
        selection=UOM_CODES,
        string="UoM Code(PK)",
        help="Unit of Measure(UoM) is a standard unit to express quantities of stock or products.",
    )
    l10n_pk_edi_transaction_type = fields.Selection(
        selection=TRANSACTION_TYPE,
        string="Transaction Type(PK)",
        default='75',
        required=True,
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    # -------------------------------------------------------------------------
    # Validation Methods
    # -------------------------------------------------------------------------

    def _l10n_pk_edi_export_check(self):
        """Validate products for E-Invoicing compliance."""

        def _group_by_error_code(product):
            if any(not product[field] for field in (
                'l10n_pk_edi_hs_code',
                'l10n_pk_edi_uom_code',
                'l10n_pk_edi_transaction_type',
            )):
                return 'product_value_missing'
            elif (
                product.l10n_pk_edi_hs_code
                and not HS_CODE_REGEX.match(product.l10n_pk_edi_hs_code)
            ):
                return 'product_hscode_invalid'
            return False

        error_messages = {
            'product_value_missing': self.env._(
                "Product(s) must have a HS Code, UoM Code and Transaction Type."
            ),
            'product_hscode_invalid': self.env._(
                "Product(s) has an invalid HS Code. It must follow the format 0000.0000 (8 digits)."
            ),
        }

        alerts = {}
        for error_code, invalid_record in self.grouped(_group_by_error_code).items():
            if not error_code:
                continue

            alerts[f'l10n_pk_edi_{error_code}'] = {
                'level': 'danger',
                'message': error_messages[error_code],
                'action_text': self.env._("View Product(s)"),
                'action': invalid_record._get_records_action(name=self.env._("Check Product(s)")),
            }
        return alerts
