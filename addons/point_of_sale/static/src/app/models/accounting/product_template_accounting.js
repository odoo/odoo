/** @odoo-module native */
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { formatCurrency } from "@web/core/currency";
import { makeLogger } from "@web/core/debug/debug_logger";
import { _t } from "@web/core/translation";
import { roundPrecision } from "@web/core/utils/format/numbers";

import { Base } from "../related_models/index.js";

import { DateTime } from "luxon";
const log = makeLogger("pos.product.pricing");

export class ProductTemplateAccounting extends Base {
    static pythonModel = "product.template";

    prepareProductBaseLineForTaxesComputationExtraValues(opts = {}) {
        const {
            price = false,
            pricelist = false,
            fiscalPosition = false,
            priceExtra = 0,
        } = opts;
        const isVariant = Boolean(this?.product_tmpl_id);
        const config = this.models["pos.config"].getFirst();
        const productTemplate = isVariant ? this.product_tmpl_id : this;
        const baseP = productTemplate.getPrice(
            pricelist,
            1,
            priceExtra,
            false,
            isVariant ? this : false,
        );
        const priceUnit = price || price === 0 ? price : baseP;
        const currency = config.currency_id;

        let taxes = this.taxes_id;

        if (fiscalPosition) {
            taxes = fiscalPosition.getTaxesAfterFiscalPosition(taxes);
        }

        return {
            currency_id: currency,
            product_id: this,
            quantity: 1,
            price_unit: priceUnit,
            tax_ids: taxes,
            ...opts,
        };
    }

    getPrice(
        pricelist,
        quantity,
        price_extra = 0,
        recurring = false,
        variant = false,
        original_line = false,
        related_lines = [],
    ) {
        if (recurring && !pricelist) {
            alert(
                _t(
                    "An error occurred when loading product prices. " +
                        "Make sure all pricelists are available in the POS.",
                ),
            );
        }

        const product = variant;
        const productTmpl = variant.product_tmpl_id || this;
        const standardPrice = variant ? variant.standard_price : this.standard_price;
        const basePrice = variant ? variant.lst_price : this.list_price;
        let price = basePrice + (price_extra || 0);

        if (!pricelist) {
            log.logic("getPrice: no pricelist", () => ({
                template: productTmpl.id,
                variant: product?.id,
                price,
            }));
            return price;
        }

        if (original_line && original_line.isLotTracked() && product) {
            related_lines.push(
                ...original_line.order_id.lines.filter(
                    (line) => line.product_id.id === product.id,
                ),
            );
            quantity = related_lines.reduce((sum, line) => sum + line.getQuantity(), 0);
        }

        const byMinQtyThenId = (a, b) => b.min_quantity - a.min_quantity || b.id - a.id;
        const tmplRules = (
            productTmpl.backLink("<-product.pricelist.item.product_tmpl_id") || []
        )
            .filter((rule) => rule.pricelist_id.id === pricelist.id && !rule.product_id)
            .sort(byMinQtyThenId);
        const productRules = (
            product?.backLink?.("<-product.pricelist.item.product_id") || []
        )
            .filter((rule) => rule.pricelist_id.id === pricelist.id)
            .sort(byMinQtyThenId);

        const tmplRulesSet = new Set(tmplRules.map((rule) => rule.id));
        const productRulesSet = new Set(productRules.map((rule) => rule.id));
        const generalRulesIds = pricelist.getGeneralRulesIdsByCategories(
            this.parentCategories,
        );
        const now = DateTime.now();
        const rules = this.models["product.pricelist.item"]
            .readMany([...productRulesSet, ...tmplRulesSet, ...generalRulesIds])
            .filter(
                (r) =>
                    (!r.min_quantity || r.min_quantity <= quantity) &&
                    (!r.date_start || r.date_start <= now) &&
                    (!r.date_end || r.date_end >= now),
            );

        const rule = rules.length && rules[0];
        log.logic("getPrice: rule", () => ({
            template: productTmpl.id,
            variant: product?.id,
            pricelist: pricelist.id,
            quantity,
            candidates: {
                product: productRules.length,
                template: tmplRules.length,
                general: generalRulesIds.length,
                applicable: rules.length,
            },
            rule: rule
                ? { id: rule.id, base: rule.base, compute: rule.compute_price }
                : null,
        }));
        if (!rule) {
            return price;
        }
        if (rule.base === "pricelist") {
            if (rule.base_pricelist_id) {
                price = this.getPrice(
                    rule.base_pricelist_id,
                    quantity,
                    0,
                    true,
                    variant,
                );
            }
        } else if (rule.base === "standard_price") {
            price = standardPrice;
        }

        if (rule.compute_price === "fixed") {
            price = rule.fixed_price;
        } else if (rule.compute_price === "percentage") {
            price = price - price * (rule.percent_price / 100);
        } else {
            const price_limit = price;
            price -= price * (rule.price_discount / 100);
            if (rule.price_round) {
                price = roundPrecision(price, rule.price_round);
            }
            if (rule.price_surcharge) {
                price += rule.price_surcharge;
            }
            if (rule.price_min_margin) {
                price = Math.max(price, price_limit + rule.price_min_margin);
            }
            if (rule.price_max_margin) {
                price = Math.min(price, price_limit + rule.price_max_margin);
            }
        }
        log.logic("getPrice: result", () => ({
            template: productTmpl.id,
            variant: product?.id,
            pricelist: pricelist.id,
            rule: rule.id,
            basePrice,
            price,
        }));

        return price;
    }

    getBaseLine(opts = {}) {
        const vals = opts.overridedValues || {};
        const {
            price = false,
            pricelist = false,
            fiscalPosition = false,
            priceExtra = 0,
        } = vals;

        return accountTaxHelpers.prepare_base_line_for_taxes_computation(
            {},
            this.prepareProductBaseLineForTaxesComputationExtraValues({
                price,
                pricelist,
                fiscalPosition,
                priceExtra,
                ...vals,
            }),
        );
    }

    getTaxDetails(opts = {}) {
        const config = this.models["pos.config"].getFirst();
        const baseLine = this.getBaseLine(opts);
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, config.company_id);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], config.company_id);
        return baseLine.tax_details;
    }

    get displayPriceUnit() {
        const config = this.models["pos.config"].getFirst();
        const price =
            config.iface_tax_included === "total"
                ? this.getTaxDetails().total_included
                : this.getTaxDetails().total_excluded;
        return formatCurrency(price, config.currency_id.id);
    }
}
