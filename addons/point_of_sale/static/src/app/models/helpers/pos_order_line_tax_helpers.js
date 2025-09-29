import { Base } from "../related_models";
import { formatCurrency } from "../utils/currency";
import { _t } from "@web/core/l10n/translation";
import { accountTaxHelpers } from "@account/helpers/account_tax";

/**
 * This module provides tax-related helper methods for the PosOrderline model.
 *
 * We keep these methods separate to facilitate future refactoring and potential reuse.
 * The methods here are focused on tax calculations and related price computations.
 */
export class PosOrderlineTaxHelpers extends Base {
    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const order = this.order_id;
        const currency = order.config.currency_id;
        const extraValues = { currency_id: currency };
        const product = this.getProduct();
        const priceUnit = this.unitPrice;
        const discount = this.getDiscount();

        const values = {
            ...extraValues,
            quantity: this.qty,
            price_unit: priceUnit,
            discount: discount,
            tax_ids: this.tax_ids,
            product_id: product,
            rate: 1.0,
            is_refund: this.qty * priceUnit < 0,
            ...customValues,
        };
        if (order.fiscal_position_id) {
            values.tax_ids = order.fiscal_position_id.getTaxes(values.tax_ids);
        }
        return values;
    }

    getTaxDetails(opts = {}) {
        const { qty = this.qty, beforeDiscount = false } = opts;
        const company = this.company;
        const product = this.getProduct();
        const taxes = this.tax_ids || product.taxes_id;
        const params = {
            quantity: qty,
            tax_ids: taxes,
        };

        if (beforeDiscount) {
            params.discount = 0.0;
        }

        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues(params)
        );
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, company);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], company);
        return baseLine;
    }

    // TODO: replace by a getter in master
    getTaxedlstUnitPrice() {
        const data = this.product_id.product_tmpl_id.getTaxDetails({
            price: this.product_id.list_price,
        });
        return data.tax_details.total_included;
    }

    // TODO: replace by a getter in master
    getBasePrice() {
        return this.currency.round(
            this.unitPrice * this.getQuantity() * (1 - this.getDiscount() / 100)
        );
    }

    // TODO: replace by a getter in master
    getComboTotalPrice() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce(
            (total, line) => total + line.getTaxDetails().tax_details.total_included,
            0
        );
    }

    // TODO: replace by a getter in master
    getComboTotalPriceWithoutTax() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((total, line) => total + line.getBasePrice() / line.qty, 0);
    }

    // This must be the only method used to get the price of an orderline
    get price() {
        if (this.getDiscountStr() === "100") {
            return _t("Free");
        }

        let price = 0;
        const isCombo = this.isPartOfCombo();
        const taxDetails = this.getTaxDetails().tax_details;

        // Price isn't shown for combo children
        if (isCombo && this.combo_parent_id) {
            return false;
        }

        if (this.config.iface_tax_included === "total") {
            price = isCombo ? this.getComboTotalPrice() : taxDetails.total_included;
        } else {
            price = isCombo ? this.getComboTotalPriceWithoutTax() : taxDetails.total_excluded;
        }

        return price;
    }

    // This must be the only method used to get the unit price of an orderline
    get unitPrice() {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        return ProductPrice.round(this.price_unit || 0);
    }

    get formattedPrice() {
        return formatCurrency(this.price, this.currency);
    }

    get formattedUnitPrice() {
        return formatCurrency(this.unitPrice, this.currency);
    }

    getUnitDisplayPriceBeforeDiscount() {
        if (this.config.iface_tax_included === "total") {
            return this.getTaxDetails({ beforeDiscount: true }).tax_details.total_included;
        } else {
            return this.getTaxDetails({ beforeDiscount: true }).tax_details.total_excluded;
        }
    }

    // FIXME: must be removed in master
    getUnitPrice() {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        return ProductPrice.round(this.price_unit || 0);
    }

    // FIXME: must be removed in master
    getDisplayPrice() {
        if (this.config.iface_tax_included === "total") {
            return this.getTaxDetails().tax_details.total_included;
        } else {
            return this.getTaxDetails().tax_details.total_excluded;
        }
    }

    // FIXME: must be removed in master
    getPriceString() {
        return this.formattedPrice;
    }

    // FIXME: must be removed in master
    get unitDisplayPrice() {
        const prices =
            this.combo_line_ids.length > 0
                ? this.combo_line_ids.reduce(
                      (acc, cl) => ({
                          priceWithTax:
                              acc.total_included +
                              cl.getTaxDetails({ qty: 1 }).tax_details.total_included,
                          total_excluded:
                              acc.total_excluded +
                              cl.getTaxDetails({ qty: 1 }).tax_details.total_excluded,
                      }),
                      { total_included: 0, total_excluded: 0 }
                  )
                : this.getTaxDetails({ qty: 1 }).tax_details;

        return this.config.iface_tax_included === "total"
            ? prices.total_included
            : prices.total_excluded;
    }

    // FIXME: must be removed in master
    getPriceWithoutTax() {
        return this.allPrices.priceWithoutTax;
    }

    // FIXME: must be removed in master
    getPriceWithTax() {
        return this.allPrices.priceWithTax;
    }

    // FIXME: must be removed in master
    getTax() {
        return this.allPrices.tax;
    }

    // FIXME: must be removed in master
    get allPrices() {
        return this.getAllPrices();
    }

    // FIXME: must be removed in master
    get allUnitPrices() {
        return this.getAllPrices(1);
    }

    // FIXME: must be removed in master
    // TODO: Don't forget to clean tests
    getAllPrices(qty = this.getQuantity()) {
        const baseLine = this.getTaxDetails({ qty });
        const baseLineNoDiscount = this.getTaxDetails({ qty, beforeDiscount: true });
        const taxDetails = {};

        for (const taxData of baseLine.tax_details.taxes_data) {
            taxDetails[taxData.tax.id] = {
                amount: taxData.tax_amount_currency,
                base: taxData.base_amount_currency,
            };
        }

        return {
            priceWithTax: baseLine.tax_details.total_included_currency,
            priceWithoutTax: baseLine.tax_details.total_excluded_currency,
            priceWithTaxBeforeDiscount: baseLineNoDiscount.tax_details.total_included_currency,
            priceWithoutTaxBeforeDiscount: baseLineNoDiscount.tax_details.total_excluded_currency,
            taxDetails: taxDetails,
            taxesData: baseLine.tax_details.taxes_data,
            tax:
                baseLine.tax_details.total_included_currency -
                baseLine.tax_details.total_excluded_currency,
        };
    }

    // FIXME: must be removed in master
    getlstPrice() {
        return this.product_id.getPrice(
            this.config.pricelist_id,
            1,
            this.price_extra,
            false,
            this.product_id
        );
    }
}
