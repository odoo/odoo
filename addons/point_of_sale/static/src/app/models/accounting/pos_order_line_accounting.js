import { formatCurrency } from "@web/core/currency";
import { Base } from "../related_models";
import { accountTaxHelpers } from "@account/helpers/account_tax";
import { _t } from "@web/core/l10n/translation";

export class PosOrderlineAccounting extends Base {
    static accountingFields = new Set([
        "order_id",
        "qty",
        "price_unit",
        "discount",
        "tax_ids",
        "price_type",
        "price_extra",
    ]);

    /**
     * Display price in the currency format, depending on the tax configuration (included or excluded).
     *
     * All getters in this section are used in XML files, their goal is to be shown in the UI.
     */
    get currencyDisplayPrice() {
        if (this.combo_parent_id) {
            return "";
        }

        if (this.getDiscount() === 100) {
            return _t("Free");
        }

        return formatCurrency(this.displayPrice, this.currency.id);
    }
    get currencyDisplayPriceUnit() {
        return formatCurrency(this.displayPriceUnit, this.currency.id);
    }
    get currencyDisplayPriceUnitExcl() {
        return formatCurrency(this.displayPriceUnitExcl, this.currency.id);
    }

    /**
     * Display price depending on the tax configuration (included or excluded).
     */
    get displayPrice() {
        return !this.combo_line_ids.length
            ? this.config.iface_tax_included === "total"
                ? this.priceIncl
                : this.priceExcl
            : this.combo_line_ids.reduce((total, cl) => {
                  const price =
                      this.config.iface_tax_included === "total" ? cl.priceIncl : cl.priceExcl;
                  return total + price;
              }, 0);
    }
    get displayPriceNoDiscount() {
        return !this.combo_line_ids.length
            ? this.config.iface_tax_included === "total"
                ? this.priceInclNoDiscount
                : this.priceExclNoDiscount
            : this.combo_line_ids.reduce((total, cl) => {
                  const price =
                      this.config.iface_tax_included === "total"
                          ? cl.priceInclNoDiscount
                          : cl.priceExclNoDiscount;
                  return total + price;
              }, 0);
    }
    get displayPriceUnit() {
        return this.config.iface_tax_included === "total"
            ? this.unitPrices.total_included
            : this.unitPrices.total_excluded;
    }
    get displayPriceUnitExcl() {
        return this.unitPrices.total_excluded;
    }
    get displayPriceUnitNoDiscount() {
        return this.config.iface_tax_included === "total"
            ? this.unitPrices.no_discount_total_included
            : this.unitPrices.no_discount_total_excluded;
    }

    get priceIncl() {
        return this.currency.round(this.prices.total_included * this.order_id.orderSign);
    }
    get priceExcl() {
        return this.currency.round(this.prices.total_excluded * this.order_id.orderSign);
    }
    get priceInclNoDiscount() {
        return this.currency.round(
            this.prices.no_discount_total_included * this.order_id.orderSign
        );
    }
    get priceExclNoDiscount() {
        return this.currency.round(
            this.prices.no_discount_total_excluded * this.order_id.orderSign
        );
    }

    /**
     * Return all prices details of an orderlines based on the order prices computation.
     * This is the preferred way to get prices of an orderline since its rounded globally.
     */
    get prices() {
        const data = this.order_id.prices.baseLineByLineUuids[this.uuid];
        return data.tax_details;
    }

    /**
     * Same as "get prices" but the prices are computed as if the quantity was 1.
     */
    get unitPrices() {
        const data = this.order_id.unitPrices.baseLineByLineUuids[this.uuid];
        return data.tax_details;
    }

    get productProductPrice() {
        return this.product_id.getPrice(
            this.config.pricelist_id,
            1,
            this.price_extra,
            false,
            this.product_id
        );
    }

    get comboTotalPrice() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((total, line) => total + line.displayPrice, 0);
    }

    get comboTotalPriceWithoutTax() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((total, line) => total + line.displayPriceUnitExcl, 0);
    }

    get comboTotalBasePrice() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((total, line) => total + line.basePriceUnit, 0);
    }

    get taxGroupLabels() {
        return this.tax_ids
            ?.map((tax) => tax.tax_group_id?.pos_receipt_label)
            .filter((label) => label)
            .join(" ");
    }

    delete(record, opts = {}) {
        const order = this.order_id;
        const result = super.delete(record, opts);
        order?.triggerRecomputeAllPrices();
        return result;
    }

    get basePrice() {
        return this.qty * this.basePriceUnit;
    }

    get basePriceUnit() {
        return this.price_unit * (1 - this.getDiscount() / 100);
    }

    /**
     * Prepare extra values for the base line used in taxes computation.
     */
    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const order = this.order_id;
        const currency = this.config.currency_id;
        const extraValues = { currency_id: currency };
        const product = this.getProduct();
        const productUom = this.getUnit();
        const priceUnit = this.price_unit || 0;
        const discount = this.getDiscount();
        const values = {
            ...extraValues,
            quantity: this.qty,
            price_unit: priceUnit,
            discount: discount,
            tax_ids: this.tax_ids,
            product_id: product,
            product_uom_id: productUom,
            rate: 1.0,
            is_refund: this.qty * priceUnit < 0,
            ...customValues,
        };
        if (order?.fiscal_position_id && product !== this.config.discount_product_id) {
            // Recompute taxes based on product and fiscal position.
            values.tax_ids = order.fiscal_position_id.getTaxesAfterFiscalPosition(values.tax_ids);
        }
        return values;
    }

    /**
     * Get the base line for taxes computation.
     */
    getBaseLine(opts = {}) {
        return accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues({
                price_unit: this.price_unit,
                quantity: this.getQuantity(),
                tax_ids: this.tax_ids,
                ...opts,
            })
        );
    }
}
