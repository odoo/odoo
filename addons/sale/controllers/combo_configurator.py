from datetime import datetime

from odoo.http import Controller, request, route
from odoo.libs.debug_log import DebugLog
from odoo.tools import groupby

_debug = DebugLog(__name__)


class SaleComboConfiguratorController(Controller):
    @route(
        route="/sale/combo_configurator/get_data",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def sale_combo_configurator_get_data(
        self,
        product_tmpl_id,
        quantity,
        date,
        currency_id=None,
        company_id=None,
        pricelist_id=None,
        selected_combo_items=None,
        **kwargs,
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = request.env["product.template"].browse(product_tmpl_id)
        currency = request.env["res.currency"].browse(currency_id)
        pricelist = request.env["product.pricelist"].browse(pricelist_id)
        date = datetime.fromisoformat(date)
        selected_combo_item_dict = {
            item["id"]: item for item in selected_combo_items or []
        }
        _debug.perf.count(
            "combo_configurator_data",
            template=product_template,
            preselected=len(selected_combo_item_dict),
        )

        return {
            "product_tmpl_id": product_tmpl_id,
            "display_name": product_template.display_name,
            "quantity": quantity,
            "price": product_template._get_configurator_display_price(
                product_template, quantity, date, currency, pricelist, **kwargs
            )[0],
            "combos": [
                {
                    "id": combo.id,
                    "name": combo.name,
                    "combo_items": [
                        self._get_combo_item_data(
                            combo,
                            combo_item,
                            selected_combo_item_dict.get(combo_item.id, {}),
                            date,
                            currency,
                            pricelist,
                            quantity=quantity,
                            **kwargs,
                        )
                        for combo_item in combo.combo_item_ids
                        if combo_item.product_id.active
                    ],
                }
                for combo in product_template.sudo().combo_ids
            ],
            "currency_id": currency_id,
            **product_template._get_additional_configurator_data(
                product_template, date, currency, pricelist, quantity=quantity, **kwargs
            ),
        }

    @route(
        route="/sale/combo_configurator/get_price",
        type="jsonrpc",
        auth="user",
        readonly=True,
    )
    def sale_combo_configurator_get_price(
        self,
        product_tmpl_id,
        quantity,
        date,
        currency_id=None,
        company_id=None,
        pricelist_id=None,
        **kwargs,
    ):
        if company_id:
            request.update_context(allowed_company_ids=[company_id])
        product_template = request.env["product.template"].browse(product_tmpl_id)
        currency = request.env["res.currency"].browse(currency_id)
        pricelist = request.env["product.pricelist"].browse(pricelist_id)
        date = datetime.fromisoformat(date)

        _debug.pipeline(
            "combo_configurator_price",
            template=product_template,
            pricelist=pricelist,
            quantity=quantity,
        )
        return product_template._get_configurator_display_price(
            product_template, quantity, date, currency, pricelist, **kwargs
        )[0]

    def _get_combo_item_data(
        self,
        combo,
        combo_item,
        selected_combo_item,
        date,
        currency,
        pricelist,
        **kwargs,
    ):
        is_configurable = any(
            ptal.attribute_id.create_variant == "no_variant" and ptal._is_configurable()
            for ptal in combo_item.product_id.attribute_line_ids
        ) or any(
            ptav.is_custom
            for ptav in combo_item.product_id.product_template_attribute_value_ids
        )
        is_preselected = len(combo.combo_item_ids) == 1 and not is_configurable
        _debug.logic(
            "combo_item_data",
            combo=combo,
            item=combo_item,
            configurable=is_configurable,
            preselected=is_preselected,
        )

        return {
            "id": combo_item.id,
            "extra_price": combo_item.currency_id._convert(
                combo_item.extra_price,
                currency,
                request.env.company,
                date,
            )
            if currency
            else combo_item.extra_price,
            "is_preselected": is_preselected,
            "is_selected": bool(selected_combo_item) or is_preselected,
            "is_configurable": is_configurable,
            "product": {
                "id": combo_item.product_id.id,
                "product_tmpl_id": combo_item.product_id.product_tmpl_id.id,
                "display_name": combo_item.product_id.display_name,
                "ptals": self._get_ptals_data(
                    combo_item.product_id, selected_combo_item, date, currency
                ),
                "description": combo_item.product_id.description_sale,
                **request.env["product.template"]._get_additional_configurator_data(
                    combo_item.product_id, date, currency, pricelist, **kwargs
                ),
            },
        }

    def _get_ptals_data(self, product, selected_combo_item, date=None, currency=None):
        variant_ptavs = product.product_template_attribute_value_ids
        no_variant_ptavs = request.env["product.template.attribute.value"].browse(
            selected_combo_item.get("no_variant_ptav_ids")
        )
        preselected_ptavs = product.attribute_line_ids.filtered(
            lambda ptal: not ptal._is_configurable()
        ).product_template_value_ids

        ptavs_by_ptal_id = dict(
            groupby(
                variant_ptavs | no_variant_ptavs | preselected_ptavs,
                lambda ptav: ptav.attribute_line_id.id,
            )
        )

        custom_ptavs = selected_combo_item.get("custom_ptavs", [])
        custom_value_by_ptav_id = {ptav["id"]: ptav["value"] for ptav in custom_ptavs}
        _debug.perf.count(
            "combo_ptals_resolved",
            product=product,
            lines=len(ptavs_by_ptal_id),
            custom=len(custom_value_by_ptav_id),
        )

        return [
            {
                "id": ptal.id,
                "name": ptal.attribute_id.name,
                "create_variant": ptal.attribute_id.create_variant,
                "selected_ptavs": self._get_selected_ptavs_data(
                    ptavs_by_ptal_id.get(ptal.id, []),
                    custom_value_by_ptav_id,
                    date,
                    currency,
                ),
            }
            for ptal in product.attribute_line_ids
        ]

    def _get_selected_ptavs_data(
        self, selected_ptavs, custom_value_by_ptav_id, date=None, currency=None
    ):
        return [
            {
                "id": ptav.id,
                "name": ptav.name,
                "price_extra": ptav.currency_id._convert(
                    ptav.price_extra,
                    currency,
                    request.env.company,
                    date,
                )
                if currency
                else ptav.price_extra,
                "custom_value": custom_value_by_ptav_id.get(ptav.id),
            }
            for ptav in selected_ptavs
        ]
