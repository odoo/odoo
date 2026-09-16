from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from ..tools import debug_log as dbg


class ResPartner(models.Model):
    _name = "res.partner"
    _inherit = ["res.partner", "mixin.pos.load"]

    _pos_data_incremental = True
    _pos_data_incremental_fields = (
        "write_date",
        "country_id.write_date",
        "state_id.write_date",
        "state_id.country_id.write_date",
    )

    pos_order_count = fields.Integer(
        compute="_compute_pos_order_count",
        groups="point_of_sale.group_pos_user",
        help="The number of point of sales orders related to this customer",
    )
    pos_order_ids = fields.One2many(
        comodel_name="pos.order",
        inverse_name="partner_id",
        readonly=True,
    )
    pos_contact_address = fields.Char(
        string="PoS Address",
        compute="_compute_pos_contact_address",
    )
    invoice_emails = fields.Char(
        compute="_compute_invoice_emails",
        readonly=True,
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Automatic Fiscal Position",
        compute="_compute_fiscal_position_id",
        help="Fiscal positions are used to adapt taxes and accounts for particular "
        "customers or sales orders/invoices. The default value comes from the customer.",
    )

    @api.depends(
        lambda self: [
            *self._display_address_depends(),
            "country_id.name",
            "country_id.code",
            "country_id.address_format",
            "state_id.name",
            "state_id.code",
        ]
    )
    @api.depends_context("lang")
    def _compute_pos_contact_address(self):
        for partner in self:
            partner.pos_contact_address = partner._display_address(without_company=True)

    def _get_application_statistics(self):
        data_list = super()._get_application_statistics()
        if not self.env.user.has_group("point_of_sale.group_pos_user"):
            return data_list
        for partner in self.filtered("pos_order_count"):
            stat_info = {
                "iconClass": "fa-solid fa-bag-shopping",
                "value": partner.pos_order_count,
                "label": _("Shopping cart"),
                "tagClass": "o_tag_color_7",
            }
            data_list[partner.id].append(stat_info)
        return data_list

    @api.model
    @dbg.timed
    def get_new_partner(self, config_id, domain, offset):
        config = self.env["pos.config"].browse(config_id)
        config.check_access("read")
        self = self._with_pos_company(config)
        domain = list(domain)
        if len(domain) == 0:
            limited_partner_ids = {
                partner[0] for partner in config.get_limited_partners_loading(offset)
            }
            domain += [("id", "in", list(limited_partner_ids))]
            new_partners = self.search(domain)
        else:
            new_partners = self.search(domain, offset=offset, limit=100)
        fiscal_positions = new_partners.fiscal_position_id
        dbg.pipeline.debug(
            "[load:res.partner] on demand config=%s offset=%s %s -> %s fpos=%s",
            config_id,
            offset,
            "ranked" if not domain or domain[-1][0] == "id" else "searched",
            dbg.rec(new_partners),
            dbg.rec(fiscal_positions),
        )
        partner_data = {"res.partner": self._load_pos_data_read(new_partners, config)}
        return {
            **partner_data,
            "res.country": self.env["res.country"]._load_pos_data_search_read(
                partner_data, config
            ),
            "res.country.state": self.env[
                "res.country.state"
            ]._load_pos_data_search_read(partner_data, config),
            "phone.number": new_partners.phone_ids._load_pos_data_read(
                new_partners.phone_ids, config
            ),
            "account.fiscal.position": self.env[
                "account.fiscal.position"
            ]._load_pos_data_read(fiscal_positions, config),
        }

    @api.model
    def _load_pos_data_domain(self, data, config):
        loaded_order_partner_ids = {
            order["partner_id"]
            for order in data.get("pos.order") or []
            if order.get("partner_id")
        }

        limited_partner_ids = {
            partner[0] for partner in config.get_limited_partners_loading()
        }

        limited_partner_ids.add(self.env.user.partner_id.id)
        partner_ids = limited_partner_ids.union(loaded_order_partner_ids)
        dbg.logic.debug(
            "[load:res.partner] %d ranked + %d from open orders -> %d",
            len(limited_partner_ids),
            len(loaded_order_partner_ids),
            len(partner_ids),
        )
        return [("id", "in", list(partner_ids))]

    @api.depends_context("company")
    @api.depends("property_account_position_id", "country_id", "state_id", "zip", "vat")
    def _compute_fiscal_position_id(self):
        for partner in self:
            partner.fiscal_position_id = (
                self.env["account.fiscal.position"]
                .with_company(self.env.company)
                ._get_fiscal_position(partner)
            )

    @api.model
    def _load_pos_data_fields(self, config):
        return [
            "id",
            "name",
            "street",
            "street2",
            "city",
            "state_id",
            "country_id",
            "vat",
            "lang",
            "phone_ids",
            "zip",
            "email",
            "barcode",
            "write_date",
            "property_product_pricelist",
            "parent_name",
            "pos_contact_address",
            "invoice_emails",
            "fiscal_position_id",
            "is_company",
            "property_account_receivable_id",
        ]

    def _compute_pos_order_count(self):
        self._update_order_count(
            "pos.order", "pos_order_count", "point_of_sale.group_pos_user"
        )

    @api.depends("email", "child_ids.type", "child_ids.email")
    def _compute_invoice_emails(self):
        for record in self:
            emails = [record.email] if record.email else []
            emails.extend(
                [
                    child.email
                    for child in record.child_ids
                    if child.type == "invoice" and child.email
                ]
            )
            record.invoice_emails = ", ".join(emails) if emails else ""

    def action_view_pos_order(self):
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "point_of_sale.action_pos_pos_form"
        )
        if self.is_company:
            action["domain"] = [("partner_id.commercial_partner_id", "=", self.id)]
        else:
            action["domain"] = [("partner_id", "=", self.id)]
        return action

    def open_commercial_entity(self):
        return {
            **super().open_commercial_entity(),
            **({"target": "new"} if self.env.context.get("target") == "new" else {}),
        }

    @api.ondelete(at_uninstall=False)
    def _unlink_if_pos_no_orders(self):
        if self.sudo().pos_order_ids:
            dbg.logic.debug(
                "res.partner unlink refused: %s has pos orders", dbg.rec(self)
            )
            raise ValidationError(
                _(
                    "You cannot delete a customer that has point of sales orders. You can archive it instead."
                )
            )
