# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain


class SaleOrderTemplate(models.Model):
    _name = "sale.order.template"
    _description = "Order Templates"
    _order = "sequence, id"

    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the Order template without removing it.",
    )
    company_id = fields.Many2one(comodel_name="res.company", default=lambda self: self.env.company)

    name = fields.Char(string="Template", required=True)
    note = fields.Html(string="Terms and conditions", translate=True)
    sequence = fields.Integer(default=10)
    template_type = fields.Selection(
        string="Type",
        selection=[("quotation", "Quotation"), ("section", "Section")],
        default="quotation",
        required=True,
    )

    mail_template_id = fields.Many2one(
        comodel_name="mail.template",
        string="Confirmation Mail",
        domain=[("model", "=", "sale.order")],
        help="This e-mail template will be sent on confirmation. Leave empty to send nothing.",
    )
    number_of_days = fields.Integer(
        string="Quotation Duration",
        help="Number of days for the validity date computation of the quotation",
    )

    require_signature = fields.Boolean(
        string="Online Signature",
        compute="_compute_require_signature",
        store=True,
        readonly=False,
        help="Request a online signature to the customer in order to confirm orders automatically.",
    )
    require_payment = fields.Boolean(
        string="Online Payment",
        compute="_compute_require_payment",
        store=True,
        readonly=False,
        help="Request an online payment to the customer in order to confirm orders automatically.",
    )
    prepayment_percent = fields.Float(
        string="Prepayment percentage",
        compute="_compute_prepayment_percent",
        store=True,
        readonly=False,
        help="The percentage of the amount needed to be paid to confirm quotations.",
    )

    sale_order_template_line_ids = fields.One2many(
        comodel_name="sale.order.template.line",
        inverse_name="sale_order_template_id",
        string="Lines",
        copy=True,
    )
    journal_id = fields.Many2one(
        "account.journal",
        string="Invoicing Journal",
        domain=[("type", "=", "sale")],
        company_dependent=True,
        check_company=True,
        help="If set, SO with this template will invoice in this journal; "
        "otherwise the sales journal with the lowest sequence is used.",
    )

    # Access control and visibility fields
    share_template = fields.Boolean(string="Share", default=True)
    team_ids = fields.Many2many(string="Sales Team", comodel_name="crm.team")
    user_has_access = fields.Boolean(
        string="Can User access",
        compute="_compute_user_has_access",
        search="_search_user_has_access",
    )

    # === COMPUTE METHODS ===#

    @api.depends("company_id")
    def _compute_require_signature(self):
        for order in self:
            order.require_signature = (
                order.company_id or order.env.company
            ).portal_confirmation_sign

    @api.depends("company_id")
    def _compute_require_payment(self):
        for order in self:
            order.require_payment = (order.company_id or order.env.company).portal_confirmation_pay

    @api.depends("company_id", "require_payment")
    def _compute_prepayment_percent(self):
        for template in self:
            template.prepayment_percent = (
                template.company_id or template.env.company
            ).prepayment_percent

    @api.depends_context("uid")
    @api.depends("team_ids", "share_template", "team_ids.member_ids", "team_ids.user_id")
    def _compute_user_has_access(self):
        for template in self:
            template.user_has_access = (
                template.share_template
                and (
                    not template.team_ids
                    or self.env.user in template.team_ids.member_ids
                    or self.env.user in template.team_ids.user_id
                )
            ) or template.create_uid == self.env.user

    def _search_user_has_access(self, operator, value):
        if operator not in {"=", "!="}:
            return NotImplemented

        if (operator == "=" and value) or (operator == "!=" and not value):
            x2many_operator = "in"
        else:
            x2many_operator = "not in"

        return (
            Domain("share_template", operator, value)
            & (
                Domain("team_ids", operator, not value)
                | Domain("team_ids.member_ids", x2many_operator, self.env.user.ids)
                | Domain("team_ids.user_id", x2many_operator, self.env.user.ids)
            )
        ) | Domain("create_uid", x2many_operator, self.env.user.ids)

    # === ONCHANGE METHODS ===#

    @api.onchange("prepayment_percent")
    def _onchange_prepayment_percent(self):
        for template in self:
            if not template.prepayment_percent:
                template.require_payment = False

    # === CONSTRAINT METHODS ===#

    @api.constrains("company_id", "sale_order_template_line_ids")
    def _check_company_id(self):
        for template in self:
            restricted_products = template.sale_order_template_line_ids.product_id.filtered(
                "company_id"
            )
            if not restricted_products:
                continue

            if not template.company_id:
                raise ValidationError(
                    _(
                        "Your template cannot contain products from specific companies if it's"
                        " shared between companies. Please restrict the template access, or remove"
                        " those products."
                    )
                )

            authorized_products = restricted_products.filtered_domain(
                self.env["product.product"]._check_company_domain(template.company_id)
            )
            if unauthorized_products := restricted_products - authorized_products:
                unaccessible_companies = unauthorized_products.company_id
                if len(unaccessible_companies) > 1:
                    raise ValidationError(
                        _(
                            "Your template belongs to company %(template_company)s but contains"
                            " products from other companies (%(product_company)s) that are not"
                            " accessible to %(template_company)s.\nPlease change the company of"
                            " your template or remove the products from other companies.",
                            product_company=", ".join(
                                unaccessible_companies.mapped("display_name")
                            ),
                            template_company=template.company_id.display_name,
                        )
                    )

                raise ValidationError(
                    _(
                        "Your template belongs to company %(template_company)s but contains"
                        " products from company (%(product_company)s) that are not"
                        " accessible to %(template_company)s.\nPlease change the company of your"
                        " template or remove the products from other companies.",
                        product_company=unaccessible_companies.display_name,
                        template_company=template.company_id.display_name,
                    )
                )

    @api.constrains("prepayment_percent")
    def _check_prepayment_percent(self):
        for template in self:
            if template.require_payment and not (0 < template.prepayment_percent <= 1.0):
                raise ValidationError(_("Prepayment percentage must be a valid percentage."))

    # === CRUD METHODS ===#

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._update_product_translations()
        return records

    def write(self, vals):
        if "active" in vals and not vals.get("active"):
            companies = (
                self.env["res.company"].sudo().search([("sale_order_template_id", "in", self.ids)])
            )
            companies.sale_order_template_id = None
        result = super().write(vals)
        self._update_product_translations()
        return result

    def _update_product_translations(self):
        languages = self.env["res.lang"].search([("active", "=", True)])
        for lang in languages:
            for line in self.sale_order_template_line_ids:
                if line.name == line.product_id.get_product_multiline_description_sale():
                    line.with_context(lang=lang.code).name = line.product_id.with_context(
                        lang=lang.code
                    ).get_product_multiline_description_sale()

    @api.model
    def _demo_configure_template(self):
        demo_template = self.env.ref(
            "sale_management.sale_order_template_1", raise_if_not_found=False
        )
        if not demo_template or demo_template.sale_order_template_line_ids:
            # Skip if template not found, or already configured
            return

        acoustic_bloc_screen_product = self.env.ref(
            "product.product_template_acoustic_bloc_screens"
        ).product_variant_id
        chair_protection_product = self.env.ref(
            "sale.product_product_1_product_template"
        ).product_variant_id
        demo_template.sale_order_template_line_ids = [
            Command.create({
                "name": self.env._("Regular Section"),
                "display_type": "line_section",
                "product_uom_qty": 0,
            }),
            Command.create({
                "product_id": self.env.ref(
                    "product.product_template_dining_table"
                ).product_variant_id.id
            }),
            Command.create({"product_id": self.env.ref("product.monitor_stand").id}),
            Command.create({
                "name": self.env._("Hidden Composition Section"),
                "display_type": "line_section",
                "collapse_composition": True,
                "product_uom_qty": 0,
            }),
            Command.create({"product_id": self.env.ref("product.consu_delivery_02").id}),
            Command.create({
                "product_id": self.env.ref("product.product_delivery_01").id,
                "product_uom_qty": 8,
            }),
            Command.create({
                "name": self.env._("Hidden Prices Section"),
                "display_type": "line_section",
                "collapse_prices": True,
                "product_uom_qty": 0,
            }),
            Command.create({"product_id": acoustic_bloc_screen_product.id}),
            Command.create({"product_id": chair_protection_product.id, "product_uom_qty": 8}),
            Command.create({
                "name": self.env._("Optional Section"),
                "display_type": "line_section",
                "is_optional": True,
                "product_uom_qty": 0,
            }),
            Command.create({
                "product_id": self.env.ref("product.product_product_16").id,
                "product_uom_qty": 0,
            }),
            Command.create({
                "name": self.env._("Subsection"),
                "display_type": "line_subsection",
                "product_uom_qty": 0,
            }),
            Command.create({
                "product_id": self.env.ref("product.product_product_12").id,
                "product_uom_qty": 0,
            }),
        ]

    # === PUBLIC ===#

    @api.model
    def get_section_templates(self, company_id):
        """Return section templates created by the current user for the given company and its
        accessible branches.

        :param int company_id: ID of the company to fetch templates for
        :return: Section templates
        :rtype: list[dict]
        """
        company = self.env["res.company"].browse(company_id)
        domain = (
            Domain("template_type", "=", "section")
            & Domain("user_has_access", "=", True)
            & self._check_company_domain(company)
        )
        return self.search_read(domain, fields=["id", "name", "create_uid"], load="")

    def prepare_section_template_order_lines(self, order_changes, fields_spec):
        """Prepare `sale.order.line` value dicts from a section template.

        Builds order line values from the given section template, applies
        `sale.order.line` onchange with provided order-level changes, and
        returns the resulting values ready for insertion.

        :param dict order_changes: Order values to consider for onchange
        :param dict fields_spec: Fields specification for onchange
        :return: Prepared sale order line values
        :rtype: list[dict]
        """
        self.ensure_one()
        result = []

        for line in self.sale_order_template_line_ids:
            onchange_values = {**line._prepare_order_line_values(), **order_changes}
            onchange_result = self.env["sale.order.line"].onchange(onchange_values, [], fields_spec)
            result.append(onchange_result.get("value", {}))

        return result

    def unlink_section_template(self):
        """Unlink the template with sudo if it is a section template.

        :return: Whether the template was unlinked
        :rtype: bool
        """
        self.ensure_one()
        if self.template_type == "section":
            # .sudo because we allow salesman to delete their own templates
            return self.sudo().unlink()

        return False
