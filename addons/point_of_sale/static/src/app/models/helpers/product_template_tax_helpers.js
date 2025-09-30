import { accountTaxHelpers } from "@account/helpers/account_tax";
import { Base } from "../related_models";
import { roundPrecision } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";

/**
 * This module provides tax-related helper methods for the PosOrderline model.
 *
 * We keep these methods separate to facilitate future refactoring and potential reuse.
 * The methods here are focused on tax calculations and related price computations.
 */
export class ProductTemplateTaxHelpers extends Base {
    prepareProductBaseLineForTaxesComputationExtraValues(
        price,
        pricelist = false,
        fiscalPosition = false,
        overridedValues = {}
    ) {
        const config = this.models["pos.config"].getFirst();
        const productTemplate = this.product_tmpl_id || this;
        const basePrice = this?.lst_price || productTemplate.getPrice(pricelist, 1);
        const priceUnit = price || price === 0 ? price : basePrice;
        const currency = config.currency_id;
        const extraValues = { currency_id: currency };

        let taxes = this.taxes_id;

        // Fiscal position.
        if (fiscalPosition) {
            taxes = fiscalPosition.getTaxes(taxes);
        }

        return {
            ...extraValues,
            product_id: this,
            quantity: 1,
            price_unit: priceUnit,
            tax_ids: taxes,
            ...overridedValues,
        };
    }

    getTaxDetails(opts = {}) {
        const {
            price = false,
            pricelist = false,
            fiscalPosition = false,
            overridedValues = {},
        } = opts;
        const config = this.models["pos.config"].getFirst();
        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            {},
            this.prepareProductBaseLineForTaxesComputationExtraValues(
                price,
                pricelist,
                fiscalPosition,
                overridedValues
            )
        );

        accountTaxHelpers.add_tax_details_in_base_line(baseLine, config.company_id);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], config.company_id);

        return baseLine;
    }

    // Port of _get_product_price on product.pricelist.
    //
    // Anything related to UOM can be ignored, the POS will always use
    // the default UOM set on the product and the user cannot change
    // it.
    //
    // Pricelist items do not have to be sorted. All
    // product.pricelist.item records are loaded with a search_read
    // and were automatically sorted based on their _order by the
    // ORM. After that they are added in this order to the pricelists.
    getPrice(pricelist, quantity, price_extra = 0, recurring = false, variant = false) {
        // In case of nested pricelists, it is necessary that all pricelists are made available in
        // the POS. Display a basic alert to the user in the case where there is a pricelist item
        // but we can't load the base pricelist to get the price when calling this method again.
        // As this method is also call without pricelist available in the POS, we can't just check
        // the absence of pricelist.
        if (recurring && !pricelist) {
            alert(
                _t(
                    "An error occurred when loading product prices. " +
                        "Make sure all pricelists are available in the POS."
                )
            );
        }

        const product = variant;
        const productTmpl = variant.product_tmpl_id || this;
        const standardPrice = variant ? variant.standard_price : this.standard_price;
        const basePrice = variant ? variant.lst_price : this.list_price;
        let price = basePrice + (price_extra || 0);

        if (!pricelist) {
            return price;
        }

        const tmplRules = (productTmpl.backLink("<-product.pricelist.item.product_tmpl_id") || [])
            .filter((rule) => rule.pricelist_id.id === pricelist.id && !rule.product_id)
            .sort((a, b) => b.min_quantity - a.min_quantity);
        const productRules = (product?.backLink?.("<-product.pricelist.item.product_id") || [])
            .filter((rule) => rule.pricelist_id.id === pricelist.id)
            .sort((a, b) => b.min_quantity - a.min_quantity);

        const tmplRulesSet = new Set(tmplRules.map((rule) => rule.id));
        const productRulesSet = new Set(productRules.map((rule) => rule.id));
        const generalRulesIds = pricelist.getGeneralRulesIdsByCategories(this.parentCategories);
        const rules = this.models["product.pricelist.item"]
            .readMany([...productRulesSet, ...tmplRulesSet, ...generalRulesIds])
            .filter((r) => r.min_quantity <= quantity);

        const rule = rules.length && rules[0];
        if (!rule) {
            return price;
        }
        if (rule.base === "pricelist") {
            if (rule.base_pricelist_id) {
                price = this.getPrice(rule.base_pricelist_id, quantity, 0, true, variant);
            }
        } else if (rule.base === "standard_price") {
            price = standardPrice;
        }

        if (rule.compute_price === "fixed") {
            price = rule.fixed_price;
        } else if (rule.compute_price === "percentage") {
            price = price - price * (rule.percent_price / 100);
        } else {
            var price_limit = price;
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

        // This return value has to be rounded with round_di before
        // being used further. Note that this cannot happen here,
        // because it would cause inconsistencies with the backend for
        // pricelist that have base == 'pricelist'.
        return price;
    }
}
