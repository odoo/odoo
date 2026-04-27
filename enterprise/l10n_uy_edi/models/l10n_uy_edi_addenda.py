from odoo import _, api, models, fields


class L10nUyEdiAddenda(models.Model):
    _name = "l10n_uy_edi.addenda"
    _description = "CFE Addenda / Disclosure"

    name = fields.Char()
    company_id = fields.Many2one("res.company", default=lambda self: self.env.company)
    type = fields.Selection([
        ("issuer", "Issuer"),
        ("receiver", "Receiver"),
        ("item", "Product/Service Detail"),
        ("cfe_doc", "CFE Document"),
        ("addenda", "Addenda"),
    ], required=True, string="Type", default="addenda")
    content = fields.Text(required=True)
    is_legend = fields.Boolean(help="It needs to be informed as a Mandatory Disclosure")

    @api.depends("type", "is_legend")
    def _compute_display_name(self):
        """
        This is needed because when we see the addenda, legends, and additional info from the move m2m tag widget
        we are not able to easily identify which type is being applied only with the name
        """
        type_name = dict(self._fields['type'].selection)
        for item in self:
            if item.is_legend:
                item.display_name = _("%(name)s (Mandatory Disclosure - %(type)s)", name=item.name, type=type_name.get(item.type))
            else:
                item.display_name = _("%(name)s (%(type)s)", name=item.name, type=type_name.get(item.type))
