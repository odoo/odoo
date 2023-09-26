/* @odoo-module */

import { PosModel, PosCollection } from "@point_of_sale/app/base_models/base";
import { uuidv4 } from "@point_of_sale/utils";
import { formatFloat, roundPrecision, roundDecimals } from "@web/core/utils/numbers";
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";

let orderline_id = 1;

export const incOrderlineId = () => {
    return orderline_id++;
};

export const getOrderlineId = () => {
    return orderline_id;
};

export const setOrderlineId = (id) => {
    orderline_id = id;
};

export class BaseOrderline extends PosModel {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.id = incOrderlineId();
        this.uuid = uuidv4();
        this.order = options.order;
        this.price_type = options.price_type || "original";
        this.product = options.product;
        this.tax_ids = options.tax_ids;
        this.set_product_lot();
        this.set_quantity(options.quantity || 1);
        this.discount = 0;
        this.note = "";
        this.hasChange = false;
        this.skipChange = false;
        this.discountStr = "0";
        this.description = "";
        this.price_extra = 0;
        this.full_product_name = options.description || "";
        this.customerNote = "";
        this.comboParent = undefined;
        this.comboLines = undefined;
        if (options.price) {
            this.set_unit_price(options.price);
        } else {
            this.set_unit_price(this.product.get_price(this.order.pricelist, this.get_quantity()));
        }
    }

    get_unit() {
        return this.product.get_unit();
    }

    set_product_lot() {
        this.has_product_lot = this.product.tracking !== "none";
        this.pack_lot_lines = this.has_product_lot && new PosCollection();
    }

    set_quantity(quant) {
        const unit = this.get_unit();
        if (unit) {
            if (unit.rounding) {
                const decimals = this.env.cache.dp["Product Unit of Measure"];
                const rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
                this.quantity = roundPrecision(quant, rounding);
                this.quantityStr = formatFloat(this.quantity, {
                    digits: [69, decimals],
                });
            } else {
                this.quantity = roundPrecision(quant, 1);
                this.quantityStr = this.quantity.toFixed(0);
            }
        } else {
            this.quantity = quant;
            this.quantityStr = "" + this.quantity;
        }
        return true;
    }

    set_unit_price(price) {
        const parsed_price = !isNaN(price)
            ? price
            : isNaN(parseFloat(price))
            ? 0
            : oParseFloat("" + price);
        this.price = roundDecimals(parsed_price || 0, this.env.cache.dp["Product Price"]);
    }

    set_discount(discount) {
        const parsed_discount =
            typeof discount === "number"
                ? discount
                : isNaN(parseFloat(discount))
                ? 0
                : oParseFloat("" + discount);
        const disc = Math.min(Math.max(parsed_discount || 0, 0), 100);
        this.discount = disc;
        this.discountStr = "" + disc;
    }

    setNote(note) {
        this.note = note;
    }

    set_customer_note(note) {
        this.customerNote = note;
    }

    get_quantity() {
        return this.quantity;
    }

    get_unit_price() {
        const digits = this.env.cache.dp["Product Price"];
        // round and truncate to mimic _symbol_set behavior
        return parseFloat(roundDecimals(this.price || 0, digits).toFixed(digits));
    }

    getNote() {
        return this.note;
    }

    get_discount() {
        return this.discount;
    }

    get_full_product_name() {
        if (this.full_product_name) {
            return this.full_product_name;
        }
        let result = this.product.display_name;
        if (this.description) {
            result += ` (${this.description})`;
        }
        return result;
    }

    get_product() {
        return this.product;
    }

    get_customer_note() {
        return this.customerNote;
    }

    get_taxes() {
        const taxes_ids = this.tax_ids || this.get_product().taxes_id;
        return this.env.utils.getTaxesByIds(taxes_ids);
    }

    display_discount_policy() {
        return this.order.pricelist ? this.order.pricelist.discount_policy : "with_discount";
    }

    generate_wrapped_product_name() {
        const MAX_LENGTH = 24; // 40 * line ratio of .6
        const wrapped = [];
        let name = this.get_full_product_name();
        let current_line = "";

        while (name.length > 0) {
            let space_index = name.indexOf(" ");

            if (space_index === -1) {
                space_index = name.length;
            }

            if (current_line.length + space_index > MAX_LENGTH) {
                if (current_line.length) {
                    wrapped.push(current_line);
                }
                current_line = "";
            }

            current_line += name.slice(0, space_index + 1);
            name = name.slice(space_index + 1);
        }

        if (current_line.length) {
            wrapped.push(current_line);
        }

        return wrapped;
    }

    compute_fixed_price(price) {
        return this.env.utils.computePriceAfterFp(price, this.get_taxes());
    }

    get_lst_price() {
        return this.product.get_price(this.env.cache.default_pricelist, 1, this.price_extra);
    }

    get_all_prices(qty = this.get_quantity()) {
        const price_unit = this.get_unit_price() * (1.0 - this.get_discount() / 100.0);

        const taxdetail = {};
        let taxtotal = 0;

        const taxes_ids = (this.tax_ids || this.product.taxes_id).filter(
            (t) => t in this.env.cache.taxes_by_id
        );
        const product_taxes = this.env.utils.get_taxes_after_fp(
            taxes_ids,
            this.order.fiscal_position
        );

        const all_taxes = this.compute_all(
            product_taxes,
            price_unit,
            qty,
            this.env.cache.currency.rounding
        );
        const all_taxes_before_discount = this.compute_all(
            product_taxes,
            this.get_unit_price(),
            qty,
            this.env.cache.currency.rounding
        );
        all_taxes.taxes.forEach(function (tax) {
            taxtotal += tax.amount;
            taxdetail[tax.id] = {
                amount: tax.amount,
                base: tax.base,
            };
        });

        return {
            priceWithTax: all_taxes.total_included,
            priceWithoutTax: all_taxes.total_excluded,
            priceWithTaxBeforeDiscount: all_taxes_before_discount.total_included,
            priceWithoutTaxBeforeDiscount: all_taxes_before_discount.total_excluded,
            tax: taxtotal,
            taxDetails: taxdetail,
        };
    }

    get_unit_display_price() {
        if (this.env.cache.config.iface_tax_included === "total") {
            return this.get_all_prices(1).priceWithTax;
        } else {
            return this.get_all_prices(1).priceWithoutTax;
        }
    }

    get_fixed_lst_price() {
        return this.compute_fixed_price(this.get_lst_price());
    }

    get_taxed_lst_unit_price() {
        const lstPrice = this.compute_fixed_price(this.get_lst_price());
        const taxesIds = this.product.taxes_id;
        const productTaxes = this.env.utils.get_taxes_after_fp(
            taxesIds,
            this.order.fiscal_position
        );
        const unitPrices = this.compute_all(
            productTaxes,
            lstPrice,
            1,
            this.env.cache.currency.rounding
        );
        if (this.env.cache.config.iface_tax_included === "total") {
            return unitPrices.total_included;
        } else {
            return unitPrices.total_excluded;
        }
    }

    get_display_price_one() {
        const rounding = this.env.cache.currency.rounding;
        const price_unit = this.get_unit_price();
        if (this.env.cache.config.iface_tax_included !== "total") {
            return roundPrecision(price_unit * (1.0 - this.get_discount() / 100.0), rounding);
        } else {
            const taxes_ids = this.tax_ids || this.product.taxes_id;
            const product_taxes = this.env.utils.get_taxes_after_fp(
                taxes_ids,
                this.order.fiscal_position
            );
            const all_taxes = this.compute_all(
                product_taxes,
                price_unit,
                1,
                this.env.cache.currency.rounding
            );

            return roundPrecision(
                all_taxes.total_included * (1 - this.get_discount() / 100),
                rounding
            );
        }
    }

    get_price_with_tax() {
        return this.get_all_prices().priceWithTax;
    }

    get_price_without_tax() {
        return this.get_all_prices().priceWithoutTax;
    }

    get_price_with_tax_before_discount() {
        return this.get_all_prices().priceWithTaxBeforeDiscount;
    }

    get_display_price() {
        if (this.env.cache.config.iface_tax_included === "total") {
            return this.get_price_with_tax();
        } else {
            return this.get_price_without_tax();
        }
    }

    get_tax() {
        return this.get_all_prices().tax;
    }

    getUnitDisplayPriceBeforeDiscount() {
        if (this.env.cache.config.iface_tax_included === "total") {
            return this.get_all_prices(1).priceWithTaxBeforeDiscount;
        } else {
            return this.get_all_prices(1).priceWithoutTaxBeforeDiscount;
        }
    }

    isPartOfCombo() {
        return Boolean(this.comboParent || this.comboLines?.length);
    }

    compute_all(taxes, price_unit, quantity, currency_rounding, handle_price_include = true) {
        return this.env.utils.compute_all(
            taxes,
            price_unit,
            quantity,
            currency_rounding,
            handle_price_include
        );
    }

    export_for_printing() {
        return {
            id: this.id,
            quantity: this.get_quantity(),
            unit_name: this.get_unit().name,
            is_in_unit: this.get_unit().id == this.env.cache.uom_unit_id,
            price: this.get_unit_display_price(),
            discount: this.get_discount(),
            product_name: this.product.display_name,
            product_name_wrapped: this.generate_wrapped_product_name(),
            price_lst: this.get_taxed_lst_unit_price(),
            fixed_lst_price: this.get_fixed_lst_price(),
            price_type: this.price_type,
            display_discount_policy: this.display_discount_policy(),
            price_display_one: this.get_display_price_one(),
            price_display: this.get_display_price(),
            price_with_tax: this.get_price_with_tax(),
            price_without_tax: this.get_price_without_tax(),
            price_with_tax_before_discount: this.get_price_with_tax_before_discount(),
            tax: this.get_tax(),
            product_description: this.product.description,
            product_description_sale: this.product.description_sale,
            pack_lot_lines: this.pack_lot_lines,
            customer_note: this.get_customer_note(),
            taxed_lst_unit_price: this.get_taxed_lst_unit_price(),
            isPartOfCombo: this.isPartOfCombo(),
            unitDisplayPriceBeforeDiscount: this.getUnitDisplayPriceBeforeDiscount(),
        };
    }
}
