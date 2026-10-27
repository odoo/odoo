from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from odoo.addons.l10n_pt_certification.const import PT_QR_NOT_SUBJECT_EXEMPTION_REASONS
from odoo.addons.l10n_pt_certification.models.account_tax import L10N_PT_TAX_EXEMPTION_PRINTED_REASONS


class L10nPtPricedDocumentMixin(models.AbstractModel):
    """
    Shared rules for Portuguese documents made of priced lines (``account.move``, ``sale.order``).

    The AT does not accept negative lines, so a discount granted on the whole document cannot be
    expressed as one: it is held here as a percentage and folded into each line's effective
    ``discount`` by ``L10nPtPricedLineMixin._set_discount``. The VAT exemption reasons carried by
    the lines are collected here as well, for the document footer.

    Models mixing this in must implement the hook:
      - ``_l10n_pt_get_lines``: the document's priced lines.
    """
    _name = 'l10n.pt.priced.document.mixin'
    _description = "Portuguese AT Document (priced lines)"

    l10n_pt_global_discount = fields.Float(
        string="Global Discount %",
        digits='Discount',
        inverse='_inverse_l10n_pt_global_discount',
    )

    def _l10n_pt_get_lines(self):
        """The document's priced lines (``invoice_line_ids``, ``order_line``, ...)."""
        raise NotImplementedError

    @api.onchange('l10n_pt_global_discount')
    def _inverse_l10n_pt_global_discount(self):
        for document in self.filtered(lambda d: d.country_code == 'PT'):
            for line in document._l10n_pt_get_lines():
                line._set_discount()

    @api.constrains('l10n_pt_global_discount')
    def _check_l10n_pt_global_discount(self):
        # The PT tax authority requires that discounts are in the range between 0% and 100%.
        for document in self.filtered(lambda d: d.country_code == 'PT'):
            if document.l10n_pt_global_discount < 0.0 or document.l10n_pt_global_discount > 100.0:
                raise ValidationError(_("Discount amounts should be between 0% and 100%."))

    def _l10n_pt_get_vat_exemptions_reasons(self):
        """Every exemption reason carried by the lines holding an exempt tax, as printed: code and mention."""
        self.ensure_one()
        return sorted({
            L10N_PT_TAX_EXEMPTION_PRINTED_REASONS[reason_code]
            for line in self._l10n_pt_get_lines()
            for reason_code in line._l10n_pt_get_line_vat_exemptions_reasons(as_string=False)
        })

    def _l10n_pt_split_not_subject_bases(self, details_by_region):
        """
        Move the base of the lines not subject to VAT out of the exempt category (``E``) of
        ``details_by_region`` (see ``_l10n_pt_get_tax_details_by_region``) into a category ``L``,
        which the QR code reports apart, in its ``L:`` field.
        """
        self.ensure_one()
        for line in self._l10n_pt_get_lines():
            # A line carries one tax, withholding taxes (negative) aside.
            tax = line.tax_ids.filtered(lambda t: t.amount >= 0)[:1]
            if tax.l10n_pt_tax_exemption_reason not in PT_QR_NOT_SUBJECT_EXEMPTION_REASONS:
                continue
            details = details_by_region.get(self._l10n_pt_get_tax_region(tax.tax_group_id), {})
            if 'E' not in details:
                continue
            details['E']['base'] -= line.price_subtotal
            details.setdefault('L', {'base': 0.0, 'vat': 0.0})['base'] += line.price_subtotal
        for details in details_by_region.values():
            if 'E' in details and self.currency_id.is_zero(details['E']['base']):
                del details['E']
        return details_by_region

    def _check_l10n_pt_lines_taxes(self):
        """
        PT requirement: All lines must have at least one tax, and in case of tax exemption, the correct tax with the
        appropriate exemption reason should be added to the line. A line carries a single tax, withholding taxes
        (negative) aside: the SAF-T (PT) has room for one tax per line.
        """
        lines = self.filtered(lambda r: r._l10n_pt_country_ok())._l10n_pt_get_lines()
        if lines.filtered(lambda l: not l.tax_ids):
            raise ValidationError(self.env._("You cannot create an invoice line without VAT tax."))
        if lines.filtered(lambda l: len(l.tax_ids.filtered(lambda t: t.amount >= 0)) > 1):
            raise ValidationError(self.env._(
                "A line can only carry one tax, withholding taxes aside. "
                "Split the line to apply several taxes."
            ))
        self._check_l10n_pt_lines_exemption_reasons()

    def _check_l10n_pt_lines_exemption_reasons(self):
        """
        PT requirement: a reason must be given whenever tax is not charged (Despacho 8632/2014 3.2.6). The
        tax itself requires one, but a tax stored before that rule may still lack it.
        """
        taxes = self.env['account.tax']
        for document in self.filtered(lambda r: r._l10n_pt_country_ok()):
            taxes |= document._l10n_pt_get_lines().tax_ids
        if taxes := taxes.filtered(lambda t: t._l10n_pt_lacks_exemption_reason()):
            raise ValidationError(self.env._(
                "A tax that charges nothing needs a VAT exemption reason: set one on %(taxes)s.",
                taxes=", ".join(taxes.mapped('name')),
            ))


class L10nPtPricedLineMixin(models.AbstractModel):
    """
    Shared rules for the priced lines of a Portuguese document (``account.move.line``,
    ``sale.order.line``).

    Models mixing this in must implement the hook:
      - ``_l10n_pt_get_document``: the document the line belongs to.
    """
    _name = 'l10n.pt.priced.line.mixin'
    _description = "Portuguese AT Document Line (priced)"

    # The default matters: it puts the key into the create values, which fires the inverse, which
    # is what applies a document-level discount to a newly added line.
    l10n_pt_line_discount = fields.Float(
        string="Line Discount",
        digits='Discount',
        default=0.0,
        inverse='_inverse_l10n_pt_line_discount',
    )

    def _l10n_pt_get_document(self):
        """The document this line belongs to (``move_id``, ``order_id``, ...)."""
        raise NotImplementedError

    def _set_discount(self):
        """
        Compute the total discount considering both the line discount and the global discount.
        Ex: A line with unit price of 100, a line discount of 10% and a global discount of 10%.
        The total discount is 19%: 1 - (1 - 0.1) * (1 - 0.1) = 0.19
        """
        self.ensure_one()
        # PT does not accept negative lines, so global discounts are held on the document and
        # folded into the line's effective discount here.
        global_discount = (self._l10n_pt_get_document().l10n_pt_global_discount or 0.0) / 100
        line_discount = (self.l10n_pt_line_discount or 0.0) / 100
        self.discount = (1 - (1 - global_discount) * (1 - line_discount)) * 100

    def _l10n_pt_keep_given_discounts(self, vals_list):
        """
        Keep the core ``discount`` given to PT lines created without a ``l10n_pt_line_discount``
        (invoices generated from PoS orders, imports, API), by making it their line discount.
        Otherwise the default line discount (0) fires the inverse, which recomputes ``discount`` from
        it and drops the given one. The given discount is the line's own: the document's global
        discount still applies on top of it.

        :param vals_list: the values the lines were created with, in the order of ``self``
        """
        lines_by_discount = defaultdict(self.browse)
        for line, vals in zip(self, vals_list):
            if (
                vals.get('discount')
                and 'l10n_pt_line_discount' not in vals
                and line._l10n_pt_get_document().country_code == 'PT'
            ):
                lines_by_discount[vals['discount']] |= line
        for discount, lines in lines_by_discount.items():
            lines.l10n_pt_line_discount = discount

    @api.onchange('l10n_pt_line_discount')
    def _inverse_l10n_pt_line_discount(self):
        for line in self.filtered(lambda l: l._l10n_pt_get_document().country_code == 'PT'):
            line._set_discount()

    @api.constrains('l10n_pt_line_discount')
    def _check_l10n_pt_line_discount(self):
        # The PT tax authority requires that discounts are in the range between 0% and 100%.
        for line in self:
            if line.l10n_pt_line_discount < 0.0 or line.l10n_pt_line_discount > 100.0:
                raise ValidationError(_("Discount amounts should be between 0% and 100%."))

    def _l10n_pt_get_line_vat_exemptions_reasons(self, as_string=True):
        """
        Returns a string with the VAT exemption reason codes per line. E.g: [M16, M19]
        It is added to the tax name in the invoice PDF to satisfy the following requirement by the
        PT tax authority: "In case the reason for exemption is not presented on the correspondent
        line, any other type of reference must be used allowing linking the exempted line to the
        correspondent reason."
        """
        self.ensure_one()
        exemption_reasons = sorted(set(
            self.tax_ids.filtered(lambda tax: tax.l10n_pt_tax_exemption_reason)
            .mapped('l10n_pt_tax_exemption_reason')
        ))
        return ", ".join(f"[{reason}]" for reason in exemption_reasons) if as_string else exemption_reasons
