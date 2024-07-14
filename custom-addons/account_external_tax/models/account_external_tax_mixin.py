# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import models, fields, api, registry, SUPERUSER_ID
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime


class AccountExternalTaxMixin(models.AbstractModel):
    """ Main class to add support for external tax integration on a model.

    This mixin can be inherited on models that should support external tax integration. Certain methods
    will need to be overridden, they are indicated below.
    """
    _name = 'account.external.tax.mixin'
    _description = 'Mixin to manage common parts of external tax calculation'

    is_tax_computed_externally = fields.Boolean(
        compute='_compute_is_tax_computed_externally',
        help='Technical field to determine if tax is calculated using an external service instead of Odoo.'
    )

    # Methods to be extended by tax calculation integrations (e.g. Avatax)
    # ====================================================================
    @api.depends('fiscal_position_id')
    def _compute_is_tax_computed_externally(self):
        """ When True external taxes will be calculated at the appropriate times. """
        self.is_tax_computed_externally = False

    def _get_external_taxes(self):
        """ Required hook that should return tax information calculated by an external service.

        :return (tuple(detail, summary)):
            detail (dict<Model, dict>): mapping between the document lines and its
                related taxes. The related taxes dict should have the following keys:
                - total: subtotal amount of this line (excl. tax)
                - tax_amount: tax amount of this line
                - tax_ids: account.tax recordset on this line
            summary (dict<Model, dict<Model<account.tax>, float>>): mapping between each tax and
                its total amount, per document.
        """
        return {}, {}

    def _uncommit_external_taxes(self):
        """ Optional hook that will be called when an invoice is put back to draft and should be uncommitted. """
        return

    def _void_external_taxes(self):
        """ Optional hook that will be called when an invoice is deleted and should be voided. """
        return

    # Methods to be extended to add support for external tax calculation on a model (e.g. account.move)
    # =================================================================================================
    def _set_external_taxes(self, mapped_taxes, summary):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        `mapped_taxes` and `summary` are the return values of `_get_external_taxes()`.
        """
        return

    def _get_and_set_external_taxes_on_eligible_records(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This method will be called automatically when taxes need to be calculated. This should filter out records
        who don't need external tax calculation (`is_tax_computed_externally` not set) and also potentially filter
        out records that are confirmed, posted or not of the right type.
        """
        return

    def _get_lines_eligible_for_external_taxes(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This method will be called to decide what document lines to pass to the external tax integration and on which
        tax will be calculated. This should filter out lines that are not "real", like section lines etc.
        """
        return []

    def _get_line_data_for_external_taxes(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This method returns model-agnostic line data to be used when doing an external tax request. It filters
        lines that should be sent to the external tax service already (via _get_lines_eligible_for_external_taxes).
        The returned dict always includes at least the following keys: id, model_name, product_id, qty,
        price_subtotal, price_unit, discount, is_refund.
        """
        return []

    def _get_date_for_external_taxes(self):
        """ Should be overridden on documents that want external tax calculation (e.g. account.move and sale.order).

        This returns the date of the record on which tax calculation should be based.
        """
        return

    # Other methods
    # ================
    def button_external_tax_calculation(self):
        self._get_and_set_external_taxes_on_eligible_records()
        return True

    def _enable_external_tax_logging(self, icp_name):
        """ Start logging requests for 30 minutes. """
        self.env['ir.config_parameter'].sudo().set_param(
            icp_name,
            (fields.Datetime.now() + timedelta(minutes=30)).strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        )

    def _log_external_tax_request(self, module_name, icp_name, message):
        """ Log when the ICP's value is in the future. """
        log_end_date = self.env['ir.config_parameter'].sudo().get_param(
            icp_name, ''
        )
        try:
            log_end_date = datetime.strptime(log_end_date, DEFAULT_SERVER_DATETIME_FORMAT)
            need_log = fields.Datetime.now() < log_end_date
        except ValueError:
            need_log = False
        if need_log:
            # This creates a new cursor to make sure the log is committed even when an
            # exception is thrown later in this request.
            self.env.flush_all()
            dbname = self._cr.dbname
            with registry(dbname).cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['ir.logging'].create({
                    'name': module_name,
                    'type': 'server',
                    'level': 'INFO',
                    'dbname': dbname,
                    'message': message,
                    'func': '',
                    'path': '',
                    'line': '',
                })
