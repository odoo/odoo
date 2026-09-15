from datetime import datetime

from odoo.http import Controller, request, route
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class SaleProductConfiguratorController(Controller):
    @route(
        route="/sale/product_configurator/get_values",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def sale_product_configurator_get_values(
        self,
        product_template_id,
        quantity,
        currency_id,
        so_date,
        product_uom_id=None,
        company_id=None,
        pricelist_id=None,
        ptav_ids=None,
        only_main_product=False,
        **kwargs,
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = self._get_product_template(product_template_id)

        combination = request.env["product.template.attribute.value"]
        if ptav_ids:
            combination = (
                request.env["product.template.attribute.value"]
                .browse(ptav_ids)
                .filtered(lambda ptav: ptav.product_tmpl_id.id == product_template_id)
            )
            unconfigured_ptals = (
                product_template.attribute_line_ids - combination.attribute_line_id
            ).filtered(lambda ptal: ptal.attribute_id.display_type != "multi")
            combination += unconfigured_ptals.mapped(
                lambda ptal: ptal.product_template_value_ids._filtered_active()[:1],
            )
        if not combination:
            combination = product_template._get_first_possible_combination()
        _debug.pipeline(
            "configurator_values",
            template=product_template,
            combination=combination,
            requested=len(ptav_ids or ()),
            only_main=only_main_product,
        )
        currency = request.env["res.currency"].browse(currency_id)
        pricelist = request.env["product.pricelist"].browse(pricelist_id)
        so_date = datetime.fromisoformat(so_date)

        return {
            "products": [
                dict(
                    **self._get_product_information(
                        product_template,
                        combination,
                        currency,
                        pricelist,
                        so_date,
                        quantity=quantity,
                        product_uom_id=product_uom_id,
                        **kwargs,
                    ),
                ),
            ],
            "optional_products": (
                [
                    dict(
                        **self._get_product_information(
                            optional_product_template,
                            optional_product_template._get_first_possible_combination(
                                parent_combination=combination,
                            ),
                            currency,
                            pricelist,
                            so_date,
                            parent_combination=product_template.attribute_line_ids.product_template_value_ids,
                            **kwargs,
                        ),
                        parent_product_tmpl_id=product_template.id,
                    )
                    for optional_product_template in product_template.optional_product_ids
                    if self._is_product_shown(optional_product_template, combination)
                ]
                if not only_main_product
                else []
            ),
            "currency_id": currency_id,
        }

    @route(
        route="/sale/product_configurator/create_product",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
    )
    def sale_product_configurator_create_product(self, product_template_id, ptav_ids):
        product_template = self._get_product_template(product_template_id)
        combination = (
            request.env["product.template.attribute.value"]
            .browse(ptav_ids)
            .filtered(lambda ptav: ptav.product_tmpl_id.id == product_template_id)
        )
        product = product_template._create_product_variant(combination)
        _debug.lifecycle(
            "configurator_variant_created",
            template=product_template,
            combination=combination,
            product=product,
        )
        return product.id

    @route(
        route="/sale/product_configurator/update_combination",
        type="jsonrpc",
        auth="user",
        methods=["POST"],
        readonly=True,
    )
    def sale_product_configurator_update_combination(
        self,
        product_template_id,
        ptav_ids,
        currency_id,
        so_date,
        quantity,
        product_uom_id=None,
        company_id=None,
        pricelist_id=None,
        **kwargs,
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = self._get_product_template(product_template_id)
        pricelist = request.env["product.pricelist"].browse(pricelist_id)
        product_uom_id = request.env["uom.uom"].browse(product_uom_id)
        currency = request.env["res.currency"].browse(currency_id)
        combination = request.env["product.template.attribute.value"].browse(ptav_ids)
        product = product_template._get_variant_for_combination(combination)
        _debug.logic(
            "configurator_combination_updated",
            template=product_template,
            combination=combination,
            variant=product,
        )

        values = self._get_basic_product_information(
            product or product_template,
            pricelist,
            combination,
            quantity=quantity or 0.0,
            uom=product_uom_id,
            currency=currency,
            date=datetime.fromisoformat(so_date),
            **kwargs,
        )
        values.pop("pricelist_rule_id", None)
        return values

    @route(
        route="/sale/product_configurator/get_optional_products",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def sale_product_configurator_get_optional_products(
        self,
        product_template_id,
        ptav_ids,
        parent_ptav_ids,
        currency_id,
        so_date,
        company_id=None,
        pricelist_id=None,
        **kwargs,
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = self._get_product_template(product_template_id)
        parent_combination = request.env["product.template.attribute.value"].browse(
            parent_ptav_ids + ptav_ids,
        )
        currency = request.env["res.currency"].browse(currency_id)
        pricelist = request.env["product.pricelist"].browse(pricelist_id)
        _debug.pipeline(
            "configurator_optional_products",
            template=product_template,
            optional=product_template.optional_product_ids,
        )
        return [
            dict(
                **self._get_product_information(
                    optional_product_template,
                    optional_product_template._get_first_possible_combination(
                        parent_combination=parent_combination,
                    ),
                    currency,
                    pricelist,
                    datetime.fromisoformat(so_date),
                    parent_combination=parent_combination,
                    **kwargs,
                ),
                parent_product_tmpl_id=product_template.id,
            )
            for optional_product_template in product_template.optional_product_ids
            if self._is_product_shown(optional_product_template, parent_combination)
        ]

    def _get_product_template(self, product_template_id):
        return request.env["product.template"].browse(product_template_id)

    def _get_product_information(
        self,
        product_template,
        combination,
        currency,
        pricelist,
        so_date,
        quantity=1,
        product_uom_id=None,
        parent_combination=None,
        show_packaging=True,
        **kwargs,
    ):
        uom = (
            product_uom_id and request.env["uom.uom"].browse(product_uom_id)
        ) or product_template.uom_id
        product = product_template._get_variant_for_combination(combination)
        attribute_exclusions = product_template._get_attribute_exclusions(
            parent_combination=parent_combination,
            combination_ids=combination.ids,
        )
        product_or_template = product or product_template
        ptals = product_template.attribute_line_ids
        attrs_map = {
            attr_data["id"]: attr_data
            for attr_data in ptals.attribute_id.read(["id", "name", "display_type"])
        }
        ptavs = ptals.product_template_value_ids.filtered(
            lambda p: p.ptav_active or (combination and p.id in combination.ids),
        )
        ptavs_map = dict(
            zip(
                ptavs.ids,
                ptavs.read(["name", "html_color", "image", "is_custom"]),
                strict=True,
            ),
        )

        values = dict(
            product_tmpl_id=product_template.id,
            **self._get_basic_product_information(
                product_or_template,
                pricelist,
                combination,
                quantity=quantity,
                uom=uom,
                currency=currency,
                date=so_date,
                **kwargs,
            ),
            quantity=quantity,
            uom=uom.read(["id", "display_name"])[0],
            attribute_lines=[
                {
                    "id": ptal.id,
                    "attribute": dict(**attrs_map[ptal.attribute_id.id]),
                    "attribute_values": [
                        dict(
                            **ptavs_map[ptav.id],
                            price_extra=self._get_ptav_price_extra(
                                ptav,
                                currency,
                                so_date,
                                product_or_template,
                            ),
                        )
                        for ptav in ptal.product_template_value_ids
                        if ptav.ptav_active
                        or (combination and ptav.id in combination.ids)
                    ],
                    "selected_attribute_value_ids": combination.filtered(
                        lambda c, ptal=ptal: ptal in c.attribute_line_id,
                    ).ids,
                    "create_variant": ptal.attribute_id.create_variant,
                }
                for ptal in product_template.attribute_line_ids
            ],
            exclusions=attribute_exclusions["exclusions"],
            archived_combinations=attribute_exclusions["archived_combinations"],
            parent_exclusions=attribute_exclusions["parent_exclusions"],
        )
        if show_packaging and product_template._has_multiple_uoms():
            _debug.logic("configurator_multiple_uoms", template=product_template)
            values["available_uoms"] = product_template._get_available_uoms().read(
                ["id", "display_name"],
            )
        values.pop("pricelist_rule_id", None)
        return values

    def _get_basic_product_information(
        self,
        product_or_template,
        pricelist,
        combination,
        **kwargs,
    ):
        basic_information = dict(
            **product_or_template.read(["description_sale", "display_name"])[0],
        )
        if not product_or_template.is_product_variant:
            basic_information["id"] = False
            combination_name = combination._get_combination_name()
            if combination_name:
                basic_information.update(
                    display_name=f"{basic_information['display_name']} ({combination_name})",
                )
        price, pricelist_rule_id = request.env[
            "product.template"
        ]._get_configurator_display_price(
            product_or_template.with_context(
                **product_or_template._prepare_product_price_context(combination),
            ),
            pricelist=pricelist,
            **kwargs,
        )
        pricelist_rule = request.env["product.pricelist.item"].browse(pricelist_rule_id)
        _debug.logic(
            "configurator_price",
            product=product_or_template,
            price=price,
            rule=pricelist_rule,
        )
        return dict(
            **basic_information,
            price=price,
            pricelist_rule_id=pricelist_rule_id,
            **request.env["product.template"]._get_additional_configurator_data(
                product_or_template,
                pricelist=pricelist,
                **kwargs,
            ),
            show_extra_price=pricelist_rule.compute_price != "fixed",
        )

    def _get_ptav_price_extra(self, ptav, currency, date, product_or_template):
        return ptav.currency_id._convert(
            ptav.price_extra,
            currency,
            request.env.company,
            date.date(),
        )

    def _is_product_shown(self, product_template, parent_combination):
        return True
