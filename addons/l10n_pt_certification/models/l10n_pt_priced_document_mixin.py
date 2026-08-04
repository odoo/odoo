from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


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
        """Every exemption reason carried by the lines holding an exempt tax."""
        self.ensure_one()
        exemption_selection = dict(self.env['account.tax']._fields['l10n_pt_tax_exemption_reason'].selection)
        return sorted({
            exemption_selection.get(reason_code)
            for line in self._l10n_pt_get_lines()
            for reason_code in line._l10n_pt_get_line_vat_exemptions_reasons(as_string=False)
        })

    def _check_l10n_pt_lines_taxes(self):
        """
        PT requirement: All lines must have at least one tax, and in case of tax exemption, the correct tax with the
        appropriate exemption reason should be added to the line.
        """
        if self.filtered(lambda r: r._l10n_pt_country_ok())._l10n_pt_get_lines().filtered(lambda l: not l.tax_ids):
            raise ValidationError(self.env._("You cannot create an invoice line without VAT tax."))


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
