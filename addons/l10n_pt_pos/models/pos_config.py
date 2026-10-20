from psycopg2.errors import UniqueViolation

from odoo import _, fields, models
from odoo.exceptions import ConcurrencyError, RedirectWarning

# The documents a PoS issues: invoice-receipts for paid sales to a customer, simplified invoices for
# anonymous ones, invoices for sales paid later, credit notes for refunds.
L10N_PT_POS_DOCUMENT_TYPES = ('out_invoice', 'out_invoice_receipt', 'out_receipt', 'out_refund')


class PosConfig(models.Model):
    _inherit = 'pos.config'

    country_code = fields.Char(related='company_id.account_fiscal_country_id.code')

    def get_limited_partners_loading(self, offset=0):
        partner_ids = super().get_limited_partners_loading(offset)
        final_consumer = self.env.ref('l10n_pt_certification.pt_final_consumer', raise_if_not_found=False)
        if final_consumer and (final_consumer.id,) not in partner_ids:
            partner_ids.append((final_consumer.id,))
        return partner_ids

    def _load_pos_data_read(self, records, config):
        data = super()._load_pos_data_read(records, config)
        if data and config.country_code == 'PT':
            final_consumer = self.env.ref('l10n_pt_certification.pt_final_consumer', raise_if_not_found=False)
            data[0]['_l10n_pt_final_consumer_id'] = final_consumer.id if final_consumer else None
        return data

    def _l10n_pt_pos_ensure_at_series(self, date=None):
        """
        The AT series this PoS issues its documents in on ``date``, creating the missing ones.

        A cashier can neither create nor register a series, and the PoS cannot show the series form
        posting would open, so the PoS provides its series itself (D-3, amended for the PoS). Looking
        them up and creating them is done as superuser, since a PoS user cannot read series either;
        they are returned in the caller's environment.
        """
        date = date or fields.Date.context_today(self)
        # sudo: PoS users have no access to AT series, see above.
        move_model = self.env['account.move'].sudo()
        needed = [
            (config.company_id, config.invoice_journal_id, document_type)
            for config in self.filtered(lambda c: c.country_code == 'PT' and c.invoice_journal_id)
            for document_type in L10N_PT_POS_DOCUMENT_TYPES
        ]
        found = {key: move_model._l10n_pt_find_at_series(*key, date) for key in needed}
        if missing := [key for key, at_series in found.items() if not at_series]:
            self._l10n_pt_pos_create_at_series(missing, date)
            found.update({key: move_model._l10n_pt_find_at_series(*key, date) for key in missing})
            if not all(found.values()):
                # Created and committed by their own transaction, after this one's snapshot was taken:
                # retry the request, which then sees them.
                raise ConcurrencyError("AT series created for the PoS in another transaction")
        return self.env['l10n_pt.at.series'].union(*found.values()).sudo(False)

    def _l10n_pt_pos_create_at_series(self, keys, date):
        """
        Create the series of ``keys`` ``(company, journal, document_type)`` in their own transaction,
        committed at once: they must outlive a refusal that rolls back the current one (a series
        without AT code, see ``_l10n_pt_pos_check_at_series``), so a manager finds them to complete.
        """
        with self.env.registry.cursor() as cr:
            # sudo: PoS users can neither read nor create AT series.
            move_model = self.env(cr=cr, su=True)['account.move']
            for company, journal, document_type in keys:
                company, journal = company.with_env(move_model.env), journal.with_env(move_model.env)
                if move_model._l10n_pt_find_at_series(company, journal, document_type, date):
                    continue  # committed by a concurrent request meanwhile
                try:
                    with cr.savepoint():
                        move_model._l10n_pt_create_at_series(journal, document_type, date)
                except UniqueViolation as e:
                    # A concurrent request is creating the same series: retry once it has committed.
                    raise ConcurrencyError(f"Concurrent creation of the AT series {document_type} of {journal.code}") from e

    def _l10n_pt_pos_check_at_series(self):
        """
        No document may be issued in a series without its AT validation code (Portaria 195/2020).
        Refuse to open the PoS rather than failing every sale at sync.
        """
        # sudo: whoever opens the PoS may not be allowed to read the series it checks.
        if missing_code := self._l10n_pt_pos_ensure_at_series().sudo().filtered(lambda s: not s.at_code):
            raise RedirectWarning(
                _(
                    "This Point of Sale issues its documents in AT series that have no AT validation code yet: "
                    "%(series)s. Register them with the AT, or enter the validation codes obtained from the "
                    "Portal das Finanças, before opening the Point of Sale.",
                    series=", ".join(missing_code.mapped('document_identifier')),
                ),
                {
                    'type': 'ir.actions.act_window',
                    'name': _('AT Series'),
                    'res_model': 'l10n_pt.at.series',
                    'view_mode': 'list,form',
                    'views': [(False, 'list'), (self.env.ref('l10n_pt_certification.view_l10n_pt_at_series_form').id, 'form')],
                    'domain': [('id', 'in', missing_code.ids)],
                },
                _('Open the AT Series'),
            )

    def _l10n_pt_pos_verify_config(self):
        self._l10n_pt_pos_check_at_series()
        if incorrect_products := self.env['product.product'].search([
            '|', ('default_code', '=', False), ('taxes_id', '=', False),
            ('available_in_pos', '=', True),
            ('combo_ids', '=', False),
            ('categ_id', 'in', self.iface_available_categ_ids.ids),
        ]):
            raise RedirectWarning(
                _("All products should have one tax and an internal reference."),
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Incorrect products',
                    'res_model': 'product.product',
                    'view_mode': 'list',
                    'views': [(self.env.ref('l10n_pt_pos.incorrect_products_view_list_pt').id, 'list'), (False, 'form')],
                    'domain': [('id', 'in', incorrect_products.ids)],
                },
                _("Incorrect products")
            )

        payment_methods = self.env['pos.payment.method'].search([('config_ids', 'in', self.ids)])
        missing_payment_mechanism = payment_methods.filtered(lambda pm: not pm.l10n_pt_pos_payment_mechanism)
        msg = ""
        if missing_payment_mechanism:
            msg += _("All payment methods available for this Point of Sale should have a payment mechanism. ")
        if msg:
            raise RedirectWarning(
                msg,
                {
                    'type': 'ir.actions.act_window',
                    'name': 'Payment Methods',
                    'res_model': 'pos.payment.method',
                    'view_mode': 'list',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('id', 'in', missing_payment_mechanism.ids)],
                },
                _("See Payment Methods"),
            )

    def open_ui(self):
        for config in self:
            if not config.company_id.country_id or config.country_code != 'PT':
                continue
            config._l10n_pt_pos_verify_config()
        return super().open_ui()
