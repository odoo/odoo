# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, _, fields
from odoo.exceptions import ValidationError
from odoo.tools import partition


class AccountExternalTaxMixinL10nBR(models.AbstractModel):
    _inherit = "account.external.tax.mixin"

    l10n_br_is_service_transaction = fields.Boolean(
        "Is Service Transaction",
        compute="_compute_l10n_br_is_service_transaction",
        help="Technical field used to determine if this transaction should be sent to the service or goods API.",
    )

    def _compute_l10n_br_is_service_transaction(self):
        """Should be overridden. Used to determine if we should treat this record as a service (NFS-e) record."""
        self.l10n_br_is_service_transaction = False

    def _l10n_br_avatax_allow_services(self):
        """Override."""
        return True

    def _l10n_br_get_operation_type(self):
        """Override."""
        return "Sale" if self.l10n_br_is_service_transaction else super()._l10n_br_get_operation_type()

    def _l10n_br_avatax_validate_lines(self, lines):
        """Override."""
        super()._l10n_br_avatax_validate_lines(lines)
        service_lines, consumable_lines = partition(
            lambda line: line["tempProduct"].product_tmpl_id._l10n_br_is_only_allowed_on_service_invoice(), lines
        )

        if not self.l10n_br_is_service_transaction:
            if service_lines:
                # Without l10n_br_edi_sale_services, all sale.order documents will be considered non-service ones because
                # of the missing _compute_l10n_br_is_service_transaction() override.
                raise ValidationError(
                    _(
                        '%s is a goods transaction but has service products:\n%s. Make sure the "Brazilian Accounting EDI for services" module is installed.',
                        self.display_name,
                        ", ".join(line["tempProduct"].display_name for line in service_lines),
                    )
                )
        else:
            if consumable_lines:
                raise ValidationError(
                    _(
                        "%s is a service transaction but has non-service products:\n%s",
                        self.display_name,
                        ", ".join(line["tempProduct"].display_name for line in consumable_lines),
                    )
                )

            errors = []

            partner = self.partner_shipping_id
            city = partner.city_id
            if not city or city.country_id.code != "BR":
                errors.append(
                    _(
                        "%s must have a city selected in the list of Brazil's cities.",
                        partner.display_name,
                    )
                )

            for line in lines:
                if not line["itemDescriptor"]["serviceCodeOrigin"]:
                    errors.append(_("%s must have a Service Code Origin.", line["tempProduct"].display_name))

            if errors:
                raise ValidationError("\n".join(errors))

    def _l10n_br_build_avatax_line(self, product, qty, unit_price, total, discount, line_id):
        """Override."""
        res = super()._l10n_br_build_avatax_line(product, qty, unit_price, total, discount, line_id)
        if not self.l10n_br_is_service_transaction:
            return res

        descriptor = res["itemDescriptor"]
        descriptor["serviceCodeOrigin"] = product.l10n_br_property_service_code_origin_id.code
        descriptor["withLaborAssignment"] = product.l10n_br_labor

        # Explicitly filter on company, this can be called via controllers which run as superuser and bypass record rules.
        service_codes = product.product_tmpl_id.l10n_br_service_code_ids.filtered(lambda code: code.company_id == self.env.company)
        descriptor["serviceCode"] = (
            service_codes.filtered(lambda code: code.city_id == self.partner_shipping_id.city_id).code
            or product.l10n_br_property_service_code_origin_id.code
        )

        del descriptor["cest"]
        del descriptor["source"]
        del descriptor["productType"]

        return res

    def _l10n_br_get_line_total(self, line_result):
        """Override. Contrary to the goods API, the service API already subtracts the discount from lineNetFigure."""
        if not self.l10n_br_is_service_transaction:
            return super()._l10n_br_get_line_total(line_result)

        return line_result["lineNetFigure"]

    def _l10n_br_update_dict_taxes_settings(self, settings, partner, iss_rate_key):
        settings.update(
            {
                "cofinsSubjectTo": partner.l10n_br_subject_cofins,
                "pisSubjectTo": partner.l10n_br_subject_pis,
                "csllSubjectTo": "T" if partner.l10n_br_is_subject_csll else "E",
            }
        )

        regime = partner.l10n_br_tax_regime
        if regime and regime.startswith("simplified"):
            settings[iss_rate_key] = partner.l10n_br_iss_simples_rate

        del settings["icmsTaxPayer"]

    def _l10n_br_update_dict_location(self, location, partner):
        location["name"] = partner.name
        location["address"]["cityName"] = partner.city_id.name

    def _l10n_br_get_calculate_payload(self):
        """Override."""
        res = super()._l10n_br_get_calculate_payload()
        if not self.l10n_br_is_service_transaction:
            return res

        locations = res["header"]["locations"]
        customer = self.partner_id
        company = self.company_id.partner_id

        self._l10n_br_update_dict_taxes_settings(
            locations["entity"]["taxesSettings"], customer, "issRfRateForSimplesTaxRegime"
        )
        self._l10n_br_update_dict_taxes_settings(
            locations["establishment"]["taxesSettings"], company, "issRfRateForSimplesTaxRegime"
        )

        self._l10n_br_update_dict_location(locations["entity"], customer)
        self._l10n_br_update_dict_location(locations["establishment"], company)

        for line in res["lines"]:
            line["benefitsAbroad"] = self.partner_shipping_id.country_id.code != "BR"

        res["header"]["messageType"] = "services"

        return res
