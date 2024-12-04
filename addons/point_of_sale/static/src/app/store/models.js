/** @odoo-module */

import { constructFullProductName, qrCodeSrc, random5Chars, uuidv4 } from "@point_of_sale/utils";
// FIXME POSREF - unify use of native parseFloat and web's parseFloat. We probably don't need the native version.
import { parseFloat as oParseFloat } from "@web/views/fields/parsers";
import {
    formatDate,
    formatDateTime,
    serializeDateTime,
    deserializeDateTime,
} from "@web/core/l10n/dates";
import {
    formatFloat,
    roundDecimals as round_di,
    roundPrecision as round_pr,
    floatIsZero,
} from "@web/core/utils/numbers";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { QRPopup } from "@point_of_sale/app/utils/qr_code_popup/qr_code_popup";
import { _t } from "@web/core/l10n/translation";
import { ConnectionLostError } from "@web/core/network/rpc";
import { renderToElement } from "@web/core/utils/render";
import { ProductCustomAttribute } from "./models/product_custom_attribute";
import { omit } from "@web/core/utils/objects";
import { ask } from "@point_of_sale/app/store/make_awaitable_dialog";

const { DateTime } = luxon;

let nextId = 0;
class PosModel {
    /**
     * Create an object with cid. If no cid is in the defaultObj,
     * cid is computed based on its id. Override _getCID if you
     * don't want this default calculation of cid.
     * @param {Object?} defaultObj its props copied to this instance.
     */
    constructor() {
        this.setup(...arguments);
    }
    // To be used by Model patches to patch constructor
    setup(defaultObj) {
        defaultObj = defaultObj || {};
        if (!defaultObj.cid) {
            defaultObj.cid = this._getCID(defaultObj);
        }
        Object.assign(this, defaultObj);
    }
    /**
     * Default cid getter. Used as local identity of this object.
     * @param {Object} obj
     */
    _getCID(obj) {
        if (obj.id) {
            if (typeof obj.id == "string") {
                return obj.id;
            } else if (typeof obj.id == "number") {
                return `c${obj.id}`;
            }
        }
        return `c${nextId++}`;
    }
}

var orderline_id = 1;

// An orderline represent one element of the content of a customer's shopping cart.
// An orderline contains a product, its quantity, its price, discount. etc.
// An Order contains zero or more Orderlines.
export class Orderline extends PosModel {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.pos = options.pos;
        this.order = options.order;
        this.price_type = options.price_type;
        this.uuid = this.uuid || uuidv4();

        this.price_type = options.price_type || "original";
        if (options.json) {
            try {
                this.init_from_JSON(options.json);
            } catch (error) {
                console.error(
                    "ERROR: attempting to recover product ID",
                    options.json.product_id[0],
                    "not available in the point of sale. Correct the product or clean the browser cache."
                );
                throw error;
            }
            return;
        }
        this.product = options.product;
        this.set_product_lot(this.product);
        options.quantity ? this.set_quantity(options.quantity) : this.set_quantity(1);
        this.discount = 0;
        this.note = this.note || "";
        this.custom_attribute_value_ids = [];
        this.hasChange = false;
        this.skipChange = false;
        this.discountStr = "0";
        this.selected = false;
        this.price_extra = 0;
        this.full_product_name = "";
        this.id = orderline_id++;
        this.customerNote = this.customerNote || "";
        this.saved_quantity = 0;

        if (options.tax_ids) {
            this.compute_related_tax(options.tax_ids);
        }

        if (options.price) {
            this.set_unit_price(options.price);
        } else {
            this.set_unit_price(this.product.get_price(this.order.pricelist, this.get_quantity()));
        }
    }

    // FIXME: this is a temporary solution. When order and orderline will use
    // related models this will be removed.
    compute_related_tax(tax_ids) {
        if (Array.isArray(tax_ids)) {
            const validTax = [];

            for (let taxId of tax_ids) {
                if (typeof taxId === "object") {
                    taxId = taxId.id;
                }

                const tax = this.pos.models["account.tax"].get(taxId);

                if (tax) {
                    validTax.push(tax);
                }
            }

            this.tax_ids = validTax.length > 0 ? validTax : [];
        }
    }

    init_from_JSON(json) {
        this.product = this.pos.models["product.product"].get(json.product_id);
        this.set_product_lot(this.product);
        this.price = json.price_unit;
        this.price_type = json.price_type || "original";
        this.set_discount(json.discount);
        this.set_quantity(json.qty, "do not recompute unit price");
        this.attribute_value_ids = json.attribute_value_ids || [];
        this.set_price_extra(json.price_extra);
        this.custom_attribute_value_ids = json.custom_attribute_value_ids.map((attr) => {
            if (attr.length > 0) {
                attr = attr[2];
            }
            return new ProductCustomAttribute(attr);
        });
        this.set_full_product_name();
        this.id = json.server_id || json.id || orderline_id++;
        orderline_id = Math.max(this.id + 1, orderline_id);
        if (this.has_product_lot) {
            var pack_lot_lines = json.pack_lot_ids;
            for (var i = 0; i < pack_lot_lines.length; i++) {
                var packlotline = pack_lot_lines[i][2];
                var pack_lot_line = new Packlotline(
                    { env: this.env },
                    { json: { ...packlotline, order_line: this } }
                );
                this.pack_lot_lines.push(pack_lot_line);
            }
        }
        this.note = json.note;
        this.tax_ids = this.compute_related_tax(
            json.tax_ids && json.tax_ids.length !== 0 ? json.tax_ids[0][2] : undefined
        );
        this.set_customer_note(json.customer_note);
        this.refunded_qty = json.refunded_qty;
        this.refunded_orderline_id = json.refunded_orderline_id;
        this.saved_quantity = json.qty;
        this.uuid = json.uuid;
        this.skipChange = json.skip_change;
        this.combo_line_id = json.combo_line_id;

        // FIXME rename to orderline_children_ids
        this.combo_line_ids = json.combo_line_ids;

        // FIXME rename to orderline_parent_id
        this.combo_parent_id = json.combo_parent_id;
    }
    clone() {
        var orderline = new Orderline(
            { env: this.env },
            {
                pos: this.pos,
                order: this.order,
                product: this.product,
                price: this.price,
            }
        );
        orderline.order = null;
        orderline.custom_attribute_value_ids = this.custom_attribute_value_ids;
        orderline.quantity = this.quantity;
        orderline.quantityStr = this.quantityStr;
        orderline.discount = this.discount;
        orderline.price = this.price;
        orderline.selected = false;
        orderline.price_type = this.price_type;
        orderline.customerNote = this.customerNote;
        orderline.note = this.note;
        return orderline;
    }
    getDisplayClasses() {
        return {};
    }
    getPackLotLinesToEdit(isAllowOnlyOneLot) {
        const currentPackLotLines = this.pack_lot_lines;
        let nExtraLines = Math.abs(this.quantity) - currentPackLotLines.length;
        nExtraLines = Math.ceil(nExtraLines);
        nExtraLines = nExtraLines > 0 ? nExtraLines : 1;
        const tempLines = currentPackLotLines
            .map((lotLine) => ({
                id: lotLine.cid,
                text: lotLine.lot_name,
            }))
            .concat(
                Array.from(Array(nExtraLines)).map((_) => ({
                    text: "",
                }))
            );
        return isAllowOnlyOneLot ? [tempLines[0]] : tempLines;
    }
    // What if a number different from 1 (or -1) is specified
    // to an orderline that has product tracked by lot? Lot tracking (based
    // on the current implementation) requires that 1 item per orderline is
    // allowed.
    async editPackLotLines() {
        const isAllowOnlyOneLot = this.product.isAllowOnlyOneLot();
        const editedPackLotLines = await this.pos.editLots(
            this.product,
            this.getPackLotLinesToEdit(isAllowOnlyOneLot)
        );
        if (!editedPackLotLines) {
            return;
        }
        this.setPackLotLines(editedPackLotLines);
        this.order.select_orderline(this);
    }
    /**
     * @param { modifiedPackLotLines, newPackLotLines }
     *    @param {Object} modifiedPackLotLines key-value pair of String (the cid) & String (the new lot_name)
     *    @param {Array} newPackLotLines array of { lot_name: String }
     */
    setPackLotLines({ modifiedPackLotLines, newPackLotLines, setQuantity = true }) {
        // Set the new values for modified lot lines.
        const lotLinesToRemove = [];
        for (const lotLine of this.pack_lot_lines) {
            const modifiedLotName = modifiedPackLotLines[lotLine.cid];
            if (modifiedLotName) {
                lotLine.lot_name = modifiedLotName;
            } else {
                // We should not call lotLine.remove() here because
                // we don't want to mutate the array while looping thru it.
                lotLinesToRemove.push(lotLine);
            }
        }

        // Remove those that needed to be removed.
        for (const lotLine of lotLinesToRemove) {
            this.pack_lot_lines = this.pack_lot_lines.filter((pll) => pll.cid !== lotLine.cid);
        }

        // Create new pack lot lines.
        let newPackLotLine;
        for (const newLotLine of newPackLotLines) {
            newPackLotLine = new Packlotline({ env: this.env }, { order_line: this });
            newPackLotLine.lot_name = newLotLine.lot_name;
            this.pack_lot_lines.push(newPackLotLine);
        }

        // Set the quantity of the line based on number of pack lots.
        if (!this.product.to_weight && setQuantity) {
            this.set_quantity_by_lot();
        }
    }
    set_product_lot(product) {
        this.has_product_lot = product.tracking !== "none";
        this.pack_lot_lines = this.has_product_lot && [];
    }
    getNote() {
        return this.note;
    }
    setNote(note) {
        this.note = note;
    }
    setHasChange(isChange) {
        this.hasChange = isChange;
    }
    // sets a discount [0,100]%
    set_discount(discount) {
        var parsed_discount =
            typeof discount === "number"
                ? discount
                : isNaN(parseFloat(discount))
                ? 0
                : oParseFloat("" + discount);
        var disc = Math.min(Math.max(parsed_discount || 0, 0), 100);
        this.discount = disc;
        this.discountStr = "" + disc;
    }
    // returns the discount [0,100]%
    get_discount() {
        return this.discount;
    }
    get_discount_str() {
        return this.discountStr;
    }
    set_price_extra(price_extra) {
        this.price_extra = parseFloat(price_extra) || 0.0;
    }
    set_full_product_name() {
        this.full_product_name = constructFullProductName(
            this,
            this.pos.models["product.template.attribute.value"].getAllBy("id"),
            this.product.display_name
        );
    }
    get_price_extra() {
        return this.price_extra;
    }
    updateSavedQuantity() {
        this.saved_quantity = this.quantity;
    }
    // sets the quantity of the product. The quantity will be rounded according to the
    // product's unity of measure properties. Quantities greater than zero will not get
    // rounded to zero
    // Return true if successfully set the quantity, otherwise, return false.
    set_quantity(quantity, keep_price) {
        this.order.assert_editable();
        var quant =
            typeof quantity === "number" ? quantity : oParseFloat("" + (quantity ? quantity : 0));
        if (this.refunded_orderline_id in this.pos.toRefundLines) {
            const toRefundDetail = this.pos.toRefundLines[this.refunded_orderline_id];
            const maxQtyToRefund =
                toRefundDetail.orderline.qty - toRefundDetail.orderline.refundedQty;
            if (quant > 0) {
                if (!this.combo_parent_id) {
                    this.env.services.dialog.add(AlertDialog, {
                        title: _t("Positive quantity not allowed"),
                        body: _t(
                            "Only a negative quantity is allowed for this refund line. Click on +/- to modify the quantity to be refunded."
                        ),
                    });
                }
                return false;
            } else if (quant == 0) {
                toRefundDetail.qty = 0;
            } else if (-quant <= maxQtyToRefund) {
                toRefundDetail.qty = -quant;
            } else {
                if (!this.combo_parent_id) {
                    this.env.services.dialog.add(AlertDialog, {
                        title: _t("Greater than allowed"),
                        body: _t(
                            "The requested quantity to be refunded is higher than the refundable quantity of %s.",
                            this.env.utils.formatProductQty(maxQtyToRefund)
                        ),
                    });
                }
                return false;
            }
        }
        var unit = this.get_unit();
        if (unit) {
            if (unit.rounding) {
                var decimals = this.pos.data.models["decimal.precision"].find(
                    (dp) => dp.name === "Product Unit of Measure"
                ).digits;
                var rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
                this.quantity = round_pr(quant, rounding);
                this.quantityStr = formatFloat(this.quantity, {
                    digits: [69, decimals],
                });
            } else {
                this.quantity = round_pr(quant, 1);
                this.quantityStr = this.quantity.toFixed(0);
            }
        } else {
            this.quantity = quant;
            this.quantityStr = "" + this.quantity;
        }

        // just like in sale.order changing the quantity will recompute the unit price
        if (!keep_price && this.price_type === "original") {
            this.set_unit_price(
                this.product.get_price(
                    this.order.pricelist,
                    this.get_quantity(),
                    this.get_price_extra()
                )
            );
            this.order.fix_tax_included_price(this);
        }
        return true;
    }
    // return the quantity of product
    get_quantity() {
        return this.quantity;
    }
    get_quantity_str() {
        return this.quantityStr;
    }
    get_lot_lines() {
        return this.pack_lot_lines && this.pack_lot_lines;
    }

    get_required_number_of_lots() {
        var lots_required = 1;

        if (this.product.tracking == "serial") {
            lots_required = Math.abs(this.quantity);
        }

        return lots_required;
    }

    get_valid_lots() {
        return this.pack_lot_lines.filter((item) => {
            return item.lot_name;
        });
    }

    set_quantity_by_lot() {
        var valid_lots_quantity = this.get_valid_lots().length;
        if (this.quantity < 0) {
            valid_lots_quantity = -valid_lots_quantity;
        }
        this.set_quantity(valid_lots_quantity);
    }

    has_valid_product_lot() {
        if (!this.has_product_lot) {
            return true;
        }
        var valid_product_lot = this.get_valid_lots();
        return this.get_required_number_of_lots() === valid_product_lot.length;
    }

    // return the unit of measure of the product
    get_unit() {
        return this.product.uom_id;
    }
    // return the product of this orderline
    get_product() {
        return this.product;
    }
    get_full_product_name() {
        return this.full_product_name || this.product.display_name;
    }
    /**
     * Return the full product name with variant details.
     *
     * e.g. Desk Organiser product with variant:
     * - Size: S
     * - Fabric: Plastic
     *
     * -> "Desk Organiser (S, Plastic)"
     * @returns {string}
     */
    get_full_product_name_with_variant() {
        const attributeValueById = Object.fromEntries(
            this.product.attribute_line_ids
                .flatMap((line) => line.product_template_value_ids)
                .map((value) => [value.id, value])
        );
        return constructFullProductName(this, attributeValueById, this.product.display_name);
    }
    // selects or deselects this orderline
    set_selected(selected) {
        this.selected = selected;
        // this trigger also triggers the change event of the collection.
    }
    // when we add an new orderline we want to merge it with the last line to see reduce the number of items
    // in the orderline. This returns true if it makes sense to merge the two
    can_be_merged_with(orderline) {
        const productPriceUnit = this.pos.data.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        ).digits;
        var price = parseFloat(
            round_di(this.price || 0, productPriceUnit).toFixed(productPriceUnit)
        );
        var order_line_price = orderline
            .get_product()
            .get_price(orderline.order.pricelist, this.get_quantity());
        order_line_price = round_di(
            orderline.compute_fixed_price(order_line_price),
            this.pos.currency.decimal_places
        );
        // only orderlines of the same product can be merged
        return (
            !this.skipChange &&
            orderline.getNote() === this.getNote() &&
            this.get_product().id === orderline.get_product().id &&
            this.is_pos_groupable() &&
            // don't merge discounted orderlines
            this.get_discount() === 0 &&
            floatIsZero(
                price - order_line_price - orderline.get_price_extra(),
                this.pos.currency.decimal_places
            ) &&
            !(
                this.product.tracking === "lot" &&
                (this.pos.pickingType.use_create_lots || this.pos.pickingType.use_existing_lots)
            ) &&
            this.full_product_name === orderline.full_product_name &&
            orderline.get_customer_note() === this.get_customer_note() &&
            !this.refunded_orderline_id &&
            !orderline.isPartOfCombo()
        );
    }
    is_pos_groupable() {
        const unit_groupable = this.product.uom_id ? this.product.uom_id.is_pos_groupable : false;
        return unit_groupable && !this.isPartOfCombo();
    }
    merge(orderline) {
        this.order.assert_editable();
        this.set_quantity(this.get_quantity() + orderline.get_quantity());
    }
    export_as_JSON() {
        var pack_lot_ids = [];
        if (this.has_product_lot) {
            this.pack_lot_lines.forEach((item) => {
                return pack_lot_ids.push([0, 0, item.export_as_JSON()]);
            });
        }

        const product = this.get_product();
        const taxes = this.tax_ids || product.taxes_id;
        return {
            uuid: this.uuid,
            skip_change: this.skipChange,
            custom_attribute_value_ids: this.custom_attribute_value_ids.map((attr) => [0, 0, attr]),
            qty: this.get_quantity(),
            price_unit: this.get_unit_price(),
            price_subtotal: this.get_price_without_tax(),
            price_subtotal_incl: this.get_price_with_tax(),
            discount: this.get_discount(),
            product_id: product.id,
            tax_ids: [[6, false, taxes.map((tax) => tax.id)]],
            id: this.id,
            pack_lot_ids: pack_lot_ids,
            attribute_value_ids: this.attribute_value_ids || [],
            full_product_name: this.get_full_product_name(),
            price_extra: this.get_price_extra(),
            customer_note: this.get_customer_note(),
            refunded_orderline_id: this.refunded_orderline_id,
            price_type: this.price_type,
            combo_line_ids: this.combo_line_ids?.map((line) => line.id),
            combo_parent_id: this.combo_parent_id?.id,
            combo_line_id: this.combo_line_id?.id,
            note: this.note,
        };
    }

    // changes the base price of the product for this orderline
    set_unit_price(price) {
        this.order.assert_editable();
        var parsed_price = !isNaN(price)
            ? price
            : isNaN(parseFloat(price))
            ? 0
            : oParseFloat("" + price);
        this.price = round_di(
            parsed_price || 0,
            this.pos.data.models["decimal.precision"].find((dp) => dp.name === "Product Price")
                .digits
        );
    }
    get_unit_price() {
        var digits = this.pos.data.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        ).digits;
        // round and truncate to mimic _symbol_set behavior
        return parseFloat(round_di(this.price || 0, digits).toFixed(digits));
    }
    get_unit_display_price() {
        if (this.pos.config.iface_tax_included === "total") {
            return this.get_all_prices(1).priceWithTax;
        } else {
            return this.get_all_prices(1).priceWithoutTax;
        }
    }
    /**
     * This is the price that will appear as striked through.
     * @returns {number | false}
     */
    get_old_unit_display_price() {
        return (
            this.display_discount_policy() === "without_discount" &&
            this.env.utils.roundCurrency(this.get_unit_display_price()) <
                this.env.utils.roundCurrency(this.get_taxed_lst_unit_price()) &&
            this.get_taxed_lst_unit_price()
        );
    }
    getUnitDisplayPriceBeforeDiscount() {
        if (this.pos.config.iface_tax_included === "total") {
            return this.get_all_prices(1).priceWithTaxBeforeDiscount;
        } else {
            return this.get_all_prices(1).priceWithoutTaxBeforeDiscount;
        }
    }
    get_base_price() {
        var rounding = this.pos.currency.rounding;
        return round_pr(
            this.get_unit_price() * this.get_quantity() * (1 - this.get_discount() / 100),
            rounding
        );
    }
    get_display_price() {
        if (this.pos.config.iface_tax_included === "total") {
            return this.get_price_with_tax();
        } else {
            return this.get_price_without_tax();
        }
    }
    get_taxed_lst_unit_price() {
        const priceUnit = this.compute_fixed_price(this.get_lst_price());
        const product = this.get_product();

        let taxes = product.taxes_id;

        // Fiscal position.
        if (this.order.fiscal_position) {
            taxes = this.pos.getTaxesAfterFiscalPosition(taxes, this.order.fiscal_position);
        }

        const taxesData = this.pos.getTaxesValues(taxes, priceUnit, 1, product);
        if (this.pos.config.iface_tax_included === "total") {
            return taxesData.total_included;
        } else {
            return taxesData.total_excluded;
        }
    }
    get_price_without_tax() {
        return this.get_all_prices().priceWithoutTax;
    }
    get_price_with_tax() {
        return this.get_all_prices().priceWithTax;
    }
    get_tax() {
        return this.get_all_prices().tax;
    }
    get_tax_details() {
        return this.get_all_prices().taxDetails;
    }
    get_taxes() {
        const taxes_ids =
            this.tax_ids && this.tax_ids.length > 0
                ? this.tax_ids.map((t) => t.id)
                : this.get_product().taxes_id.map((t) => t.id);
        return this.pos.models["account.tax"].filter((tax) => taxes_ids.includes(tax.id));
    }
    getTaxIds() {
        return this.get_taxes().map((tax) => tax.id);
    }
    /**
     * Calculate the amount of taxes of a specific Orderline, that are included in the price.
     * @returns {Number} the total amount of price included taxes
     */
    get_total_taxes_included_in_price() {
        const productTaxes = this._getProductTaxesAfterFiscalPosition();
        const taxDetails = this.get_tax_details();
        return productTaxes
            .filter((tax) => tax.price_include)
            .reduce((sum, tax) => sum + taxDetails[tax.id].amount, 0);
    }
    /**
     * Calculates the taxes for a product, and converts the taxes based on the fiscal position of the order.
     *
     * @returns {Object} The calculated product taxes after filtering and fiscal position conversion.
     */
    _getProductTaxesAfterFiscalPosition() {
        const product = this.get_product();
        let taxes = this.tax_ids || product.taxes_id;

        // Fiscal position.
        const fiscalPosition = this.order.fiscal_position;
        if (fiscalPosition) {
            taxes = this.pos.getTaxesAfterFiscalPosition(taxes, fiscalPosition);
        }

        return taxes;
    }
    get_all_prices(qty = this.get_quantity()) {
        const product = this.get_product();
        const priceUnit = this.get_unit_price();
        const discount = this.get_discount();
        const priceUnitAfterDiscount = priceUnit * (1.0 - discount / 100.0);

        let taxes = this.tax_ids || product.taxes_id;

        // Fiscal position.
        const fiscalPosition = this.order.fiscal_position;
        if (fiscalPosition) {
            taxes = this.pos.getTaxesAfterFiscalPosition(taxes, fiscalPosition);
        }

        const taxesData = this.pos.getTaxesValues(taxes, priceUnitAfterDiscount, qty, product);
        const taxesDataBeforeDiscount = this.pos.getTaxesValues(taxes, priceUnit, qty, product);

        // Tax details.
        const taxDetails = {};
        for (const taxValues of taxesData.taxes_data) {
            taxDetails[taxValues.id] = {
                amount: taxValues.tax_amount_factorized,
                base: taxValues.display_base,
            };
        }

        return {
            priceWithTax: taxesData.total_included,
            priceWithoutTax: taxesData.total_excluded,
            priceWithTaxBeforeDiscount: taxesDataBeforeDiscount.total_included,
            priceWithoutTaxBeforeDiscount: taxesDataBeforeDiscount.total_excluded,
            tax: taxesData.total_included - taxesData.total_excluded,
            taxDetails: taxDetails,
            taxValuesList: taxesData.taxes_data,
        };
    }
    display_discount_policy() {
        return this.order.pricelist ? this.order.pricelist.discount_policy : "with_discount";
    }
    compute_fixed_price(price) {
        const product = this.get_product();
        const taxes = this.tax_ids || product.taxes_id;

        // Fiscal position.
        const order = this.pos.get_order();
        if (order && order.fiscal_position) {
            price = this.pos.getPriceUnitAfterFiscalPosition(
                taxes,
                price,
                product,
                order.fiscal_position
            );
        }
        return price;
    }
    get_lst_price() {
        return this.product.get_price(this.pos.config.pricelist_id, 1, this.price_extra);
    }
    set_lst_price(price) {
        this.order.assert_editable();
        this.product.lst_price = round_di(
            parseFloat(price) || 0,
            this.pos.data.models["decimal.precision"].find((dp) => dp.name === "Product Price")
                .digits
        );
    }
    set_customer_note(note) {
        this.customerNote = note || "";
    }
    get_customer_note() {
        return this.customerNote;
    }
    get_total_cost() {
        return this.product.standard_price * this.quantity;
    }
    /**
     * Checks if the current line is a tip from a customer.
     * @returns Boolean
     */
    isTipLine() {
        const tipProduct = this.pos.config.tip_product_id;
        return tipProduct && this.product.id === tipProduct.id;
    }

    /**
     * @returns {Orderline[]} all the lines that are in the same combo tree as the given line
     * (including the given line), or just the given line if it is not part of a combo.
     */
    getAllLinesInCombo() {
        if (this.combo_parent_id) {
            // having a `combo_parent_id` means that we are not
            // at the root node of the combo tree.
            // Thus, we first navigate to the root
            return this.combo_parent_id.getAllLinesInCombo();
        }
        const lines = [];
        const stack = [this];
        while (stack.length) {
            const n = stack.pop();
            lines.push(n);
            if (n.combo_line_ids) {
                stack.push(...n.combo_line_ids);
            }
        }
        return lines;
    }
    isPartOfCombo() {
        return Boolean(this.combo_parent_id || this.combo_line_ids?.length);
    }
    getComboTotalPrice() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((total, line) => total + line.get_all_prices(1).priceWithTax, 0);
    }
    getComboTotalPriceWithoutTax() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((total, line) => total + line.get_base_price() / line.quantity, 0);
    }
    getPriceString() {
        return this.get_discount_str() === "100"
            ? // free if the discount is 100
              _t("Free")
            : this.combo_line_ids && this.combo_line_ids.length > 0
            ? // empty string if it is a combo parent line
              ""
            : this.env.utils.formatCurrency(this.get_display_price(), this.currency);
    }
    getDisplayData() {
        return {
            productName: this.get_full_product_name(),
            price: this.getPriceString(),
            qty: this.get_quantity_str(),
            unit: this.product.uom_id ? this.product.uom_id.name : "",
            unitPrice: this.env.utils.formatCurrency(this.get_unit_display_price()),
            oldUnitPrice: this.env.utils.formatCurrency(this.get_old_unit_display_price()),
            discount: this.get_discount_str(),
            customerNote: this.get_customer_note(),
            internalNote: this.getNote(),
            combo_parent_id: this.combo_parent_id
                ? this.combo_parent_id.get_full_product_name()
                : "",
            pack_lot_lines: this.get_lot_lines(),
            price_without_discount: this.env.utils.formatCurrency(
                this.getUnitDisplayPriceBeforeDiscount()
            ),
        };
    }
}

export class Packlotline extends PosModel {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        this.lot_name = null;
        this.order_line = options.order_line;
        if (options.json) {
            this.init_from_JSON(options.json);
            return;
        }
    }

    init_from_JSON(json) {
        this.order_line = json.order_line;
        this.set_lot_name(json.lot_name);
    }

    set_lot_name(name) {
        this.lot_name = String(name || "").trim() || null;
    }

    get_lot_name() {
        return this.lot_name;
    }

    export_as_JSON() {
        return {
            lot_name: this.get_lot_name(),
        };
    }
}

// Every Paymentline contains a cashregister and an amount of money.
export class Payment extends PosModel {
    setup(obj, options) {
        super.setup(...arguments);
        this.pos = options.pos;
        this.order = options.order;
        this.amount = 0;
        this.selected = false;
        this.cashier_receipt = "";
        this.ticket = "";
        this.payment_status = "";
        this.card_type = "";
        this.cardholder_name = "";
        this.transaction_id = "";

        if (options.json) {
            this.init_from_JSON(options.json);
            return;
        }
        this.payment_method = options.payment_method;
        if (this.payment_method === undefined) {
            throw new Error(_t("Please configure a payment method in your POS."));
        }
        this.name = this.payment_method.name;
    }
    init_from_JSON(json) {
        this.amount = json.amount;
        this.payment_method = this.pos.models["pos.payment.method"].get(json.payment_method_id);
        this.can_be_reversed = json.can_be_reversed;
        this.name = this.payment_method.name;
        this.payment_status = json.payment_status;
        this.ticket = json.ticket;
        this.card_type = json.card_type;
        this.cardholder_name = json.cardholder_name;
        this.transaction_id = json.transaction_id;
        this.is_change = json.is_change;
    }
    //sets the amount of money on this payment line
    set_amount(value) {
        this.order.assert_editable();
        this.amount = round_di(parseFloat(value) || 0, this.pos.currency.decimal_places);
    }
    // returns the amount of money on this paymentline
    get_amount() {
        return this.amount;
    }
    set_selected(selected) {
        if (this.selected !== selected) {
            this.selected = selected;
        }
    }
    /**
     * returns {string} payment status.
     */
    get_payment_status() {
        return this.payment_status;
    }

    /**
     * Set the new payment status.
     *
     * @param {string} value - new status.
     */
    set_payment_status(value) {
        this.payment_status = value;
    }

    /**
     * Check if paymentline is done.
     * Paymentline is done if there is no payment status or the payment status is done.
     */
    is_done() {
        return this.get_payment_status()
            ? this.get_payment_status() === "done" || this.get_payment_status() === "reversed"
            : true;
    }

    /**
     * Set info to be printed on the cashier receipt. value should
     * be compatible with both the QWeb and ESC/POS receipts.
     *
     * @param {string} value - receipt info
     */
    set_cashier_receipt(value) {
        this.cashier_receipt = value;
    }

    /**
     * Set additional info to be printed on the receipts. value should
     * be compatible with both the QWeb and ESC/POS receipts.
     *
     * @param {string} value - receipt info
     */
    set_receipt_info(value) {
        this.ticket += value;
    }

    // returns the associated cashregister
    //exports as JSON for server communication
    export_as_JSON() {
        return {
            name: serializeDateTime(DateTime.local()),
            payment_method_id: this.payment_method.id,
            amount: this.get_amount(),
            payment_status: this.payment_status,
            can_be_reversed: this.can_be_reversed,
            ticket: this.ticket,
            card_type: this.card_type,
            cardholder_name: this.cardholder_name,
            transaction_id: this.transaction_id,
        };
    }
    //exports as JSON for receipt printing
    export_for_printing() {
        return {
            amount: this.get_amount(),
            name: this.name,
            ticket: this.ticket,
        };
    }
    // If payment status is a non-empty string, then it is an electronic payment.
    // TODO: There has to be a less confusing way to distinguish simple payments
    // from electronic transactions. Perhaps use a flag?
    is_electronic() {
        return Boolean(this.get_payment_status());
    }

    async showQR() {
        let qr;
        try {
            qr = await this.env.services.orm.call("pos.payment.method", "get_qr_code", [
                [this.payment_method.id],
                this.amount,
                this.order.name,
                this.order.name,
                this.pos.currency.id,
                this.order.partner?.id,
            ]);
        } catch (error) {
            qr = this.payment_method.default_qr;
            if (!qr) {
                let message;
                if (error instanceof ConnectionLostError) {
                    message = _t(
                        "Connection to the server has been lost. Please check your internet connection."
                    );
                } else {
                    message = error.data.message;
                }
                this.env.services.dialog.add(AlertDialog, {
                    title: _t("Failure to generate Payment QR Code"),
                    body: message,
                });
                return false;
            }
        }
        return await ask(
            this.env.services.dialog,
            {
                title: _t(this.name),
                line: this,
                order: this.order,
                qrCode: qr,
            },
            {},
            QRPopup
        );
    }

    async pay() {
        this.set_payment_status("waiting");
        if (this.payment_method.payment_method_type === "qr_code") {
            return this.handle_payment_response(await this.showQR());
        }
        return this.handle_payment_response(
            await this.payment_method.payment_terminal.send_payment_request(this.cid)
        );
    }
    handle_payment_response(isPaymentSuccessful) {
        if (isPaymentSuccessful) {
            this.set_payment_status("done");
            if (this.payment_method.payment_method_type !== "qr_code") {
                this.can_be_reversed = this.payment_method.payment_terminal.supports_reversals;
            }
        } else {
            this.set_payment_status("retry");
        }
        return isPaymentSuccessful;
    }
}

// An order more or less represents the content of a customer's shopping cart (the OrderLines)
// plus the associated payment information (the Paymentlines)
// there is always an active ('selected') order in the Pos, a new one is created
// automaticaly once an order is completed and sent to the server.
export class Order extends PosModel {
    setup(_defaultObj, options) {
        super.setup(...arguments);
        var self = this;
        options = options || {};

        this.locked = false;
        this.pos = options.pos;
        this.selected_orderline = undefined;
        this.selected_paymentline = undefined;
        this.screen_data = {}; // see Gui
        this.temporary = options.temporary || false;
        this.date_order = luxon.DateTime.now();
        this.to_invoice = false;
        this.orderlines = [];
        this.paymentlines = [];
        this.pos_session_id = this.pos.session.id;
        this.cashier = this.pos.get_cashier();
        this.finalized = false; // if true, cannot be modified.
        this.shippingDate = null;
        this.combos = [];

        this.partner = null;

        this.uiState = {
            ReceiptScreen: {
                inputEmail: "",
                // if null: not yet tried to send
                // if false/true: tried sending email
                emailSuccessful: null,
                emailNotice: "",
            },
            // TODO: This should be in pos_restaurant.
            TipScreen: {
                inputTipAmount: "",
            },
        };

        if (options.json) {
            this.init_from_JSON(options.json);
            const linesById = Object.fromEntries(this.orderlines.map((l) => [l.id || l.cid, l]));
            for (const line of this.orderlines) {
                line.combo_line_ids = line.combo_line_ids
                    ?.filter((id) => linesById[id])
                    .map((id) => linesById[id]);
                const combo_parent_id = linesById[line.combo_parent_id];

                if (combo_parent_id) {
                    line.combo_parent_id = combo_parent_id;
                }

                const combo_line_id = this.pos.models["pos.combo.line"].get(line.combo_line_id);
                if (combo_line_id) {
                    line.combo_line_id = combo_line_id;
                }
            }
        } else {
            this.set_pricelist(this.pos.config.pricelist_id);
            this.sequence_number = this.pos.session.sequence_number++;
            this.access_token = uuidv4(); // unique uuid used to identify the authenticity of the request from the QR code.
            this.ticketCode = this._generateTicketCode(); // 5-digits alphanum code shown on the receipt
            this.uid = this.generate_unique_id();
            this.name = _t("Order %s", this.uid);

            if (self.pos.config.default_fiscal_position_id) {
                this.fiscal_position = this.pos.models["account.fiscal.position"].find(function (
                    fp
                ) {
                    return fp.id === self.pos.config.default_fiscal_position_id.id;
                });
            }
        }

        this.lastOrderPrepaChange = this.lastOrderPrepaChange || {};
        this.trackingNumber = (
            (this.pos_session_id % 10) * 100 +
            (this.sequence_number % 100)
        ).toString();
    }

    getEmailItems() {
        return [_t("the receipt")].concat(this.is_to_invoice() ? [_t("the invoice")] : []);
    }

    save_to_db() {
        if (!this.temporary && !this.locked && !this.finalized) {
            this.assert_editable();
            this.pos.db.save_unpaid_order(this);
        }
    }
    /**
     * Initialize PoS order from a JSON string.
     *
     * If the order was created in another session, the sequence number should be changed so it doesn't conflict
     * with orders in the current session.
     * Else, the sequence number of the session should follow on the sequence number of the loaded order.
     *
     * @param {object} json JSON representing one PoS order.
     */
    init_from_JSON(json) {
        let partner;
        if (json.state && ["done", "invoiced", "paid"].includes(json.state)) {
            this.sequence_number = json.sequence_number;
            this.pos_session_id = json.pos_session_id;
        } else if (json.pos_session_id !== this.pos.session.id) {
            this.sequence_number = this.pos.session.sequence_number++;
        } else {
            this.sequence_number = json.sequence_number;
            this.updateSequenceNumber(json);
        }
        this.session_id = this.pos.session.id;
        this.uid = json.uid;
        if (json.name) {
            this.name = json.name;
        } else {
            this.name = _t("Order %s", this.uid);
        }
        this.date_order = deserializeDateTime(json.date_order);
        this.server_id = json.server_id || json.id || false;
        this.user_id = json.user_id;

        if (json.fiscal_position_id) {
            var fiscal_position = this.pos.models["account.fiscal.position"].find(function (fp) {
                return fp.id === json.fiscal_position_id;
            });

            if (fiscal_position) {
                this.fiscal_position = fiscal_position;
            } else {
                this.fiscal_position_not_found = true;
                console.error("ERROR: trying to load a fiscal position not available in the pos");
            }
        }

        if (json.pricelist_id) {
            this.pricelist = this.pos.models["product.pricelist"].find(function (pricelist) {
                return pricelist.id === json.pricelist_id;
            });
        } else {
            this.pricelist = this.pos.config.pricelist_id;
        }

        if (json.partner_id) {
            partner = this.pos.models["res.partner"].get(json.partner_id);
            if (!partner) {
                console.error("ERROR: trying to load a partner not available in the pos");
            }
        } else {
            partner = null;
        }
        this.partner = partner;

        this.temporary = false; // FIXME
        this.to_invoice = json.to_invoice || false;
        this.shippingDate = json.shipping_date;

        var orderlines = json.lines;
        for (var i = 0; i < orderlines.length; i++) {
            var orderline = orderlines[i][2];
            const product = this.pos.models["product.product"].get(orderline.product_id);
            if (orderline.product_id && product) {
                this.add_orderline(
                    new Orderline(
                        { env: this.env },
                        { pos: this.pos, order: this, json: orderline }
                    )
                );
            }
        }

        var paymentlines = json.statement_ids;
        for (i = 0; i < paymentlines.length; i++) {
            var paymentline = paymentlines[i][2];
            var newpaymentline = new Payment(
                { env: this.env },
                { pos: this.pos, order: this, json: paymentline }
            );
            this.paymentlines.push(newpaymentline);

            if (i === paymentlines.length - 1) {
                this.select_paymentline(newpaymentline);
            }
        }

        // Tag this order as 'locked' if it is already paid.
        this.locked = ["paid", "done", "invoiced"].includes(json.state);
        this.state = json.state;
        this.amount_return = json.amount_return;
        this.account_move = json.account_move;
        this.backendId = json.id;
        this.is_tipped = json.is_tipped || false;
        this.tip_amount = json.tip_amount || 0;
        this.access_token = json.access_token || "";
        this.ticketCode = json.ticket_code || "";
        this.lastOrderPrepaChange =
            json.last_order_preparation_change && JSON.parse(json.last_order_preparation_change);
    }
    updateSequenceNumber(json) {
        this.pos.session.sequence_number = Math.max(
            this.sequence_number + 1,
            this.pos.session.sequence_number
        );
    }
    export_as_JSON() {
        var orderLines, paymentLines;
        orderLines = [];
        this.orderlines.forEach((item) => {
            return orderLines.push([0, 0, item.export_as_JSON()]);
        });
        paymentLines = [];
        this.paymentlines.forEach((item) => {
            const itemAsJson = item.export_as_JSON();
            if (itemAsJson) {
                return paymentLines.push([0, 0, itemAsJson]);
            }
        });
        var json = {
            name: this.get_name(),
            amount_paid: this.get_total_paid() - this.get_change(),
            amount_total: this.get_total_with_tax(),
            amount_tax: this.get_total_tax(),
            amount_return: this.get_change(),
            lines: orderLines,
            statement_ids: paymentLines,
            pos_session_id: this.pos_session_id,
            pricelist_id: this.pricelist ? this.pricelist.id : false,
            partner_id: this.get_partner() ? this.get_partner().id : false,
            user_id: this.pos.user.id,
            uid: this.uid,
            sequence_number: this.sequence_number,
            date_order: serializeDateTime(this.date_order),
            fiscal_position_id: this.fiscal_position ? this.fiscal_position.id : false,
            server_id: this.server_id ? this.server_id : false,
            to_invoice: this.to_invoice ? this.to_invoice : false,
            shipping_date: this.shippingDate ? this.shippingDate : false,
            is_tipped: this.is_tipped || false,
            tip_amount: this.tip_amount || 0,
            access_token: this.access_token || "",
            last_order_preparation_change: JSON.stringify(this.lastOrderPrepaChange),
            ticket_code: this.ticketCode || "",
        };
        if (!this.is_paid && this.user_id) {
            json.user_id = this.user_id;
        }
        return json;
    }
    export_for_printing() {
        // If order is locked (paid), the 'change' is saved as negative payment,
        // and is flagged with is_change = true. A receipt that is printed first
        // time doesn't show this negative payment so we filter it out.
        const paymentlines = this.paymentlines
            .filter((p) => !p.is_change)
            .map((p) => p.export_for_printing());
        return {
            orderlines: this.orderlines.map((l) => omit(l.getDisplayData(), "internalNote")),
            paymentlines,
            amount_total: this.get_total_with_tax(),
            total_without_tax: this.get_total_without_tax(),
            amount_tax: this.get_total_tax(),
            total_paid: this.get_total_paid(),
            total_discount: this.get_total_discount(),
            rounding_applied: this.get_rounding_applied(),
            tax_details: this.get_tax_details(),
            change: this.locked ? this.amount_return : this.get_change(),
            name: this.get_name(),
            invoice_id: null, //TODO
            cashier: this.cashier?.name,
            date: formatDateTime(this.date_order),
            pos_qr_code:
                this.pos.company.point_of_sale_use_ticket_qr_code &&
                (this.finalized || ["paid", "done", "invoiced"].includes(this.state)) &&
                qrCodeSrc(
                    `${this.pos.base_url}/pos/ticket/validate?access_token=${this.access_token}`
                ),
            ticket_code:
                this.pos.company.point_of_sale_ticket_unique_code &&
                this.finalized &&
                this.ticketCode,
            base_url: this.pos.base_url,
            footer: this.pos.config.receipt_footer,
            // FIXME: isn't there a better way to handle this date?
            shippingDate: this.shippingDate && formatDate(DateTime.fromSQL(this.shippingDate)),
            headerData: {
                ...this.pos.getReceiptHeaderData(this),
                trackingNumber: this.trackingNumber,
            },
        };
    }
    // This function send order change to printer
    // For sending changes to preparation display see sendChanges function.
    async printChanges(cancelled) {
        const orderChange = this.changesToOrder(cancelled);
        let isPrintSuccessful = true;
        const d = new Date();
        let hours = "" + d.getHours();
        hours = hours.length < 2 ? "0" + hours : hours;
        let minutes = "" + d.getMinutes();
        minutes = minutes.length < 2 ? "0" + minutes : minutes;
        for (const printer of this.pos.unwatched.printers) {
            const changes = this._getPrintingCategoriesChanges(
                printer.config.product_categories_ids,
                orderChange
            );
            if (changes["new"].length > 0 || changes["cancelled"].length > 0) {
                const printingChanges = {
                    new: changes["new"],
                    cancelled: changes["cancelled"],
                    table_name: this.pos.config.module_pos_restaurant
                        ? this.getTable().name
                        : false,
                    floor_name: this.pos.config.module_pos_restaurant
                        ? this.getTable().floor_id.name
                        : false,
                    name: this.name || "unknown order",
                    time: {
                        hours,
                        minutes,
                    },
                };
                const receipt = renderToElement("point_of_sale.OrderChangeReceipt", {
                    changes: printingChanges,
                });
                const result = await printer.printReceipt(receipt);
                if (!result.successful) {
                    isPrintSuccessful = false;
                }
            }
        }

        return isPrintSuccessful;
    }
    _getPrintingCategoriesChanges(categories, currentOrderChange) {
        const filterFn = (change) => {
            const product = this.pos.models["product.product"].get(change["product_id"]);
            const categoryIds = product.parentPosCategIds;

            for (const categoryId of categoryIds) {
                if (categories.includes(categoryId)) {
                    return true;
                }
            }
        };

        return {
            new: currentOrderChange["new"].filter(filterFn),
            cancelled: currentOrderChange["cancelled"].filter(filterFn),
        };
    }
    /**
     * This function is called after the order has been successfully sent to the preparation tool(s).
     * In the future, this status should be separated between the different preparation tools,
     * so that if one of them returns an error, it is possible to send the information back to it
     * without impacting the other tools.
     */
    updateLastOrderChange() {
        const orderlineIdx = [];
        this.orderlines.forEach((line) => {
            if (!line.skipChange) {
                const note = line.getNote();
                const lineKey = `${line.uuid} - ${note}`;
                orderlineIdx.push(lineKey);

                if (this.lastOrderPrepaChange[lineKey]) {
                    this.lastOrderPrepaChange[lineKey]["quantity"] = line.get_quantity();
                } else {
                    this.lastOrderPrepaChange[lineKey] = {
                        attribute_value_ids: line.attribute_value_ids,
                        line_uuid: line.uuid,
                        product_id: line.get_product().id,
                        name: line.get_full_product_name_with_variant(),
                        note: note,
                        quantity: line.get_quantity(),
                    };
                }
                line.setHasChange(false);
                line.saved_quantity = line.get_quantity();
            }
        });

        // Checks whether an orderline has been deleted from the order since it
        // was last sent to the preparation tools. If so we delete it to the changes.
        for (const lineKey in this.lastOrderPrepaChange) {
            if (!this.getOrderedLine(lineKey)) {
                delete this.lastOrderPrepaChange[lineKey];
            }
        }
    }

    /**
     * @returns {{ [lineKey: string]: { product_id: number, name: string, note: string, quantity: number } }}
     * This function recalculates the information to be sent to the preparation tools,
     * it uses the variable lastOrderPrepaChange which contains the last changes sent
     * to perform this calculation.
     */
    getOrderChanges(skipped = false) {
        const prepaCategoryIds = this.pos.orderPreparationCategories;
        const oldChanges = this.lastOrderPrepaChange;
        const changes = {};
        let changesCount = 0;
        let changeAbsCount = 0;

        // Compares the orderlines of the order with the last ones sent.
        // When one of them has changed, we add the change.
        for (const orderlineIdx in this.orderlines) {
            const orderline = this.orderlines[orderlineIdx];
            const product = orderline.get_product();
            const note = orderline.getNote();
            const lineKey = `${orderline.uuid} - ${note}`;
            const productCategoryIds = product.parentPosCategIds.filter((id) =>
                prepaCategoryIds.has(id)
            );

            if (prepaCategoryIds.size === 0 || productCategoryIds.length > 0) {
                const quantity = orderline.get_quantity();
                const quantityDiff = oldChanges[lineKey]
                    ? quantity - oldChanges[lineKey].quantity
                    : quantity;

                if (quantityDiff && orderline.skipChange === skipped) {
                    changes[lineKey] = {
                        name: orderline.get_full_product_name_with_variant(),
                        product_id: product.id,
                        attribute_value_ids: orderline.attribute_value_ids,
                        quantity: quantityDiff,
                        note: note,
                    };
                    changesCount += quantityDiff;
                    changeAbsCount += Math.abs(quantityDiff);

                    if (!orderline.skipChange) {
                        orderline.setHasChange(true);
                    }
                } else {
                    orderline.setHasChange(false);
                }
            } else {
                orderline.setHasChange(false);
            }
        }
        // Checks whether an orderline has been deleted from the order since it
        // was last sent to the preparation tools. If so we add this to the changes.
        for (const [lineKey, lineResume] of Object.entries(this.lastOrderPrepaChange)) {
            if (!this.getOrderedLine(lineKey)) {
                const lineKey = `${lineResume["line_uuid"]} - ${lineResume["note"]}`;
                if (!changes[lineKey]) {
                    changes[lineKey] = {
                        product_id: lineResume["product_id"],
                        name: lineResume["name"],
                        note: lineResume["note"],
                        attribute_value_ids: lineResume["attribute_value_ids"],
                        quantity: -lineResume["quantity"],
                    };
                } else {
                    changes[lineKey]["quantity"] -= lineResume["quantity"];
                }
            }
        }

        return {
            nbrOfChanges: changeAbsCount,
            orderlines: changes,
            count: changesCount,
        };
    }
    // This function transforms the data generated by getOrderChanges into the old
    // pattern used by the printer and the display preparation. This old pattern comes from
    // the time when this logic was in pos_restaurant.
    changesToOrder(cancelled = false) {
        const toAdd = [];
        const toRemove = [];
        const changes = !cancelled
            ? Object.values(this.getOrderChanges().orderlines)
            : Object.values(this.lastOrderPrepaChange);

        for (const lineChange of changes) {
            if (lineChange["quantity"] > 0 && !cancelled) {
                toAdd.push(lineChange);
            } else {
                lineChange["quantity"] = Math.abs(lineChange["quantity"]); // we need always positive values.
                toRemove.push(lineChange);
            }
        }

        return { new: toAdd, cancelled: toRemove };
    }
    getOrderedLine(lineKey) {
        return this.orderlines.find(
            (line) =>
                line.uuid === this.lastOrderPrepaChange[lineKey]["line_uuid"] &&
                line.note === this.lastOrderPrepaChange[lineKey]["note"]
        );
    }
    hasSkippedChanges() {
        return this.orderlines.find((orderline) => orderline.skipChange) ? true : false;
    }
    hasChangesToPrint() {
        return this.getOrderChanges().count ? true : false;
    }
    canPay() {
        return this.orderlines.length;
    }
    async pay() {
        if (!this.canPay()) {
            return;
        }
        if (
            this.orderlines.some(
                (line) => line.get_product().tracking !== "none" && !line.has_valid_product_lot()
            ) &&
            (this.pos.pickingType.use_create_lots || this.pos.pickingType.use_existing_lots)
        ) {
            const confirmed = await ask(this.env.services.dialog, {
                title: _t("Missing Serial/Lot Numbers"),
                body: _t(
                    "Some products require serial/lot numbers to be set. \nProceeding anyway will create inconsistency in your inventory, you will need to correct manually. \nProceed anyway?"
                ),
                confirmLabel: _t("Discard"),
                cancelLabel: _t("Accept the risk"),
            });
            // confirm and cancel are inverted to be displayed according to the specification...
            if (!confirmed) {
                this.pos.mobile_pane = "right";
                this.env.services.pos.showScreen("PaymentScreen");
            }
        } else {
            this.pos.mobile_pane = "right";
            this.env.services.pos.showScreen("PaymentScreen");
        }
    }
    is_empty() {
        return this.orderlines.length === 0;
    }
    get isBooked() {
        return Boolean(this.booked || !this.is_empty() || this.server_id);
    }
    generate_unique_id() {
        // Generates a public identification number for the order.
        // The generated number must be unique and sequential. They are made 12 digit long
        // to fit into EAN-13 barcodes, should it be needed

        function zero_pad(num, size) {
            var s = "" + num;
            while (s.length < size) {
                s = "0" + s;
            }
            return s;
        }
        return (
            zero_pad(this.pos.session.id, 5) +
            "-" +
            zero_pad(this.pos.session.login_number, 3) +
            "-" +
            zero_pad(this.sequence_number, 4)
        );
    }
    updateSavedQuantity() {
        this.orderlines.forEach((line) => line.updateSavedQuantity());
    }
    get_name() {
        return this.name;
    }
    assert_editable() {
        if (this.finalized) {
            throw new Error("Finalized Order cannot be modified");
        }
    }
    /* ---- Order Lines --- */
    add_orderline(line) {
        this.assert_editable();
        if (line.order) {
            line.order._unlinkOrderline(line);
        }
        line.order = this;
        this.orderlines.push(line);
        this.select_orderline(this.get_last_orderline());
    }
    get_orderline(id) {
        var orderlines = this.orderlines;
        for (var i = 0; i < orderlines.length; i++) {
            if (orderlines[i].id === id) {
                return orderlines[i];
            }
        }
        return null;
    }
    get_orderlines() {
        return this.orderlines;
    }
    /**
     * Groups the orderlines of the specific order according to the taxes applied to them. The orderlines that have
     * the exact same combination of taxes are grouped together.
     *
     * @returns {tax_ids: Orderlines[]} contains pairs of tax_ids (in csv format) and arrays of Orderlines
     * with the corresponding tax_ids.
     * e.g. {
     *  '1,2': [Orderline_A, Orderline_B],
     *  '3': [Orderline_C],
     * }
     */
    get_orderlines_grouped_by_tax_ids() {
        const orderlines_by_tax_group = {};
        const lines = this.get_orderlines();
        for (const line of lines) {
            const tax_group = this._get_tax_group_key(line);
            if (!(tax_group in orderlines_by_tax_group)) {
                orderlines_by_tax_group[tax_group] = [];
            }
            orderlines_by_tax_group[tax_group].push(line);
        }
        return orderlines_by_tax_group;
    }
    _get_tax_group_key(line) {
        return line
            ._getProductTaxesAfterFiscalPosition()
            .map((tax) => tax.id)
            .join(",");
    }
    /**
     * Calculate the amount that will be used as a base in order to apply a downpayment or discount product in PoS.
     * In our calculation we take into account taxes that are included in the price.
     *
     * @param  {String} tax_ids a string of the tax ids that are applied on the orderlines, in csv format
     * e.g. if taxes with ids 2, 5 and 6 are applied tax_ids will be "2,5,6"
     * @param  {Orderline[]} lines an srray of Orderlines
     * @return {Number} the base amount on which we will apply a percentile reduction
     */
    calculate_base_amount(tax_ids_array, lines) {
        // Consider price_include taxes use case
        const has_taxes_included_in_price = tax_ids_array.filter(
            (tax_id) =>
                this.pos.models["account.tax"].get(tax_id).price_include ||
                (this.pos.models["account.tax"].get(tax_id).children_tax_ids.length > 0 &&
                    this.pos.models["account.tax"]
                        .get(tax_id)
                        .children_tax_ids.every((child_tax) => child_tax.price_include))
        ).length;

        const base_amount = lines.reduce(
            (sum, line) =>
                sum +
                (has_taxes_included_in_price
                    ? line.get_price_with_tax()
                    : line.get_price_without_tax()),
            0
        );
        return base_amount;
    }
    get_last_orderline() {
        const orderlines = this.orderlines;
        return this.orderlines.at(orderlines.length - 1);
    }
    get_tip() {
        const tip_product = this.pos.config.tip_product_id;
        const lines = this.get_orderlines();
        if (!tip_product) {
            return 0;
        } else {
            for (var i = 0; i < lines.length; i++) {
                if (lines[i].get_product() === tip_product) {
                    return lines[i].get_unit_price();
                }
            }
            return 0;
        }
    }

    set_tip(tip) {
        const tip_product = this.pos.config.tip_product_id;
        const lines = this.get_orderlines();
        if (tip_product) {
            for (let i = 0; i < lines.length; i++) {
                if (lines[i].get_product() === tip_product) {
                    lines[i].set_unit_price(tip);
                    lines[i].set_lst_price(tip);
                    lines[i].price_type = "automatic";
                    lines[i].order.tip_amount = tip;
                    return;
                }
            }
            return this.add_product(tip_product, {
                is_tip: true,
                quantity: 1,
                price: tip,
                lst_price: tip,
                extras: { price_type: "automatic" },
            });
        }
    }
    set_fiscal_position(fiscal_position) {
        this.fiscal_position = fiscal_position;
    }
    set_pricelist(pricelist) {
        var self = this;
        this.pricelist = pricelist;

        const orderlines = this.get_orderlines();

        const lines_to_recompute = orderlines.filter(
            (line) =>
                line.price_type === "original" &&
                !(line.combo_line_ids?.length || line.combo_parent_id)
        );
        lines_to_recompute.forEach((line) => {
            line.set_unit_price(
                line.product.get_price(self.pricelist, line.get_quantity(), line.get_price_extra())
            );
            self.fix_tax_included_price(line);
        });
        const combo_parent_lines = orderlines.filter(
            (line) => line.price_type === "original" && line.combo_line_ids?.length
        );
        const attributes_prices = {};
        combo_parent_lines.forEach((parentLine) => {
            attributes_prices[parentLine.id] = this.compute_child_lines(
                parentLine.product,
                parentLine.combo_line_ids.map((childLine) => {
                    const comboLineCopy = { combo_line_id: childLine.combo_line_id };
                    if (childLine.attribute_value_ids) {
                        comboLineCopy.configuration = {
                            attribute_value_ids: childLine.attribute_value_ids,
                        };
                    }
                    return comboLineCopy;
                }),
                pricelist
            );
        });
        const combo_children_lines = orderlines.filter(
            (line) => line.price_type === "original" && line.combo_parent_id
        );
        combo_children_lines.forEach((line) => {
            line.set_unit_price(
                attributes_prices[line.combo_parent_id.id].find(
                    (item) => item.comboLine.id === line.combo_line_id.id
                ).price
            );
            self.fix_tax_included_price(line);
        });
    }

    /**
     * Performs the basic unlinking of the `line` from the order.
     * @param {Orderline} line
     */
    _unlinkOrderline(line) {
        this.assert_editable();
        const index = this.orderlines.findIndex((_item) => line.cid == _item.cid);
        if (index < 0) {
            return index;
        }
        this.orderlines.splice(index, 1);
        line.order = null;
    }

    /**
     * A wrapper around _unlinkOrderline that may potentially remove multiple orderlines.
     * In core pos, it removes the linked combo lines. In other modules, it may remove
     * other related lines, e.g. multiple reward lines in pos_loyalty module.
     * @param {Orderline} line
     * @returns {boolean} true if the line was removed, false otherwise
     */
    removeOrderline(line) {
        const linesToRemove = line.getAllLinesInCombo();
        for (const lineToRemove of linesToRemove) {
            this._unlinkOrderline(lineToRemove);
            if (lineToRemove.refunded_orderline_id in this.pos.toRefundLines) {
                delete this.pos.toRefundLines[lineToRemove.refunded_orderline_id];
            }
        }
        this.select_orderline(this.get_last_orderline());
        return true;
    }

    fix_tax_included_price(line) {
        line.set_unit_price(line.compute_fixed_price(line.price));
    }

    _isRefundOrder() {
        if (this.orderlines.length > 0 && this.orderlines[0].refunded_orderline_id) {
            return true;
        }
        return false;
    }

    add_product(product, options) {
        if (
            this.pos.doNotAllowRefundAndSales() &&
            this._isRefundOrder() &&
            (!options.quantity || options.quantity > 0)
        ) {
            this.pos.dialog.add(AlertDialog, {
                title: _t("Refund and Sales not allowed"),
                body: _t("It is not allowed to mix refunds and sales"),
            });
            return;
        }
        if (this._printed) {
            // when adding product with a barcode while being in receipt screen
            this.pos.removeOrder(this);
            return this.pos.add_new_order().add_product(product, options);
        }
        this.assert_editable();
        options = options || {};
        const quantity = options.quantity ? options.quantity : 1;
        const line = new Orderline(
            { env: this.env },
            { pos: this.pos, order: this, product: product, quantity: quantity }
        );
        this.fix_tax_included_price(line);

        if (options.comboConfigurator?.length) {
            options.price = 0;
        }

        this.set_orderline_options(line, options);
        line.set_full_product_name();
        var to_merge_orderline;
        for (var i = 0; i < this.orderlines.length; i++) {
            if (this.orderlines.at(i).can_be_merged_with(line) && options.merge !== false) {
                to_merge_orderline = this.orderlines.at(i);
            }
        }
        if (to_merge_orderline) {
            to_merge_orderline.merge(line);
            this.select_orderline(to_merge_orderline);
        } else {
            this.add_orderline(line);
            this.select_orderline(this.get_last_orderline());
        }

        if (options.comboConfigurator?.length) {
            const childLines = this.addComboLines(line, options);
            line.combo_line_ids = childLines;

            this.select_orderline(line);
        }

        if (options.draftPackLotLines) {
            this.selected_orderline.setPackLotLines({
                ...options.draftPackLotLines,
                setQuantity: options.quantity === undefined,
            });
        }

        this.hasJustAddedProduct = true;
        clearTimeout(this.productReminderTimeout);
        this.productReminderTimeout = setTimeout(() => {
            this.hasJustAddedProduct = false;
        }, 3000);
        return this.selected_orderline;
    }

    compute_child_lines(parentProduct, childLineConf, pricelist) {
        const combolines = [];
        const parentLstPrice = parentProduct.get_price(pricelist, 1);
        const originalTotal = childLineConf.reduce((acc, conf) => {
            const originalPrice = conf.combo_line_id.combo_id.base_price;
            return acc + originalPrice;
        }, 0);

        let remainingTotal = parentLstPrice;

        for (const conf of childLineConf) {
            const comboLine = conf.combo_line_id;
            const combo = comboLine.combo_id;
            let priceUnit = round_di(
                (combo.base_price * parentLstPrice) / originalTotal,
                this.pos.data.models["decimal.precision"].find((dp) => dp.name === "Product Price")
                    .digits
            );
            remainingTotal -= priceUnit;
            if (comboLine.id == childLineConf[childLineConf.length - 1].combo_line_id.id) {
                priceUnit += remainingTotal;
            }
            const attribute_value_ids = comboLine.configuration?.attribute_value_ids;
            const attributesPriceExtra = (attribute_value_ids ?? [])
                .map((attr) => attr?.price_extra || 0)
                .reduce((acc, price) => acc + price, 0);
            const totalPriceExtra = priceUnit + attributesPriceExtra + comboLine.combo_price;
            combolines.push({ comboLine: comboLine, price: totalPriceExtra, attribute_value_ids });
        }
        return combolines;
    }

    addComboLines(comboParent, options) {
        const comboLinesPrices = this.compute_child_lines(
            comboParent.product,
            options.comboConfigurator,
            this.pricelist
        );

        const comboLines = [];
        for (const comboLine of comboLinesPrices) {
            // Important to call addProductFromUi instead of addProductToCurrentOrder
            // to avoid showing the ProductConfiguratorPopup.
            // Product configuration is already done during the setup of the combo.
            const line = this.add_product(comboLine.comboLine.product_id, {
                price: comboLine.price,
                combo_parent_id: comboParent,
                combo_line_id: comboLine.comboLine,
                attribute_value_ids: comboLine.attribute_value_ids,
                extras: { price_type: "manual" },
            });

            comboLines.push(line);
        }

        return comboLines;
    }
    set_orderline_options(orderline, options) {
        if (options.quantity !== undefined) {
            orderline.set_quantity(options.quantity);
        }

        if (options.price_extra !== undefined) {
            orderline.price_extra = options.price_extra;
            orderline.set_unit_price(
                orderline.product.get_price(
                    this.pricelist,
                    orderline.get_quantity(),
                    options.price_extra
                )
            );
            this.fix_tax_included_price(orderline);
        }

        if (options.price !== undefined) {
            orderline.set_unit_price(options.price);
            this.fix_tax_included_price(orderline);
        }

        if (options.lst_price !== undefined) {
            orderline.set_lst_price(options.lst_price);
        }

        if (options.discount !== undefined) {
            orderline.set_discount(options.discount);
        }

        if (options.attribute_value_ids) {
            orderline.attribute_value_ids = options.attribute_value_ids || [];
        }

        if (
            options.attribute_custom_values &&
            Object.keys(options.attribute_custom_values).length > 0
        ) {
            const customAttributeValues = [];
            for (const [id, value] of Object.entries(options.attribute_custom_values)) {
                if (!value) {
                    continue;
                }

                customAttributeValues.push(
                    new ProductCustomAttribute({
                        custom_product_template_attribute_value_id: parseInt(id),
                        custom_value: value,
                    })
                );
            }

            orderline.custom_attribute_value_ids = customAttributeValues;
        }

        if (options.extras !== undefined) {
            for (var prop in options.extras) {
                orderline[prop] = options.extras[prop];
            }
        }
        if (options.is_tip) {
            this.is_tipped = true;
            this.tip_amount = options.price;
        }
        if (options.refunded_orderline_id) {
            orderline.refunded_orderline_id = options.refunded_orderline_id;
        }
        if (options.tax_ids) {
            orderline.compute_related_tax(options.tax_ids);
        }
        if (options.combo_parent_id) {
            orderline.combo_parent_id = options.combo_parent_id;
        }
        if (options.combo_line_id) {
            orderline.combo_line_id = options.combo_line_id;
        }
    }
    get_selected_orderline() {
        return this.selected_orderline;
    }
    select_orderline(line) {
        if (line) {
            if (line !== this.selected_orderline) {
                // if line (new line to select) is not the same as the old
                // selected_orderline, then we set the old line to false,
                // and set the new line to true. Also, set the new line as
                // the selected_orderline.
                if (this.selected_orderline) {
                    this.selected_orderline.set_selected(false);
                }
                this.selected_orderline = line;
                this.selected_orderline.set_selected(true);
            }
        } else {
            this.selected_orderline = undefined;
        }
        this.pos.numpadMode = "quantity";
    }
    /* ---- Payment Lines --- */
    add_paymentline(payment_method) {
        this.assert_editable();
        if (this.electronic_payment_in_progress()) {
            return false;
        } else {
            var newPaymentline = new Payment(
                { env: this.env },
                { order: this, payment_method: payment_method, pos: this.pos }
            );
            this.paymentlines.push(newPaymentline);
            this.select_paymentline(newPaymentline);
            if (this.pos.config.cash_rounding) {
                this.selected_paymentline.set_amount(0);
            }
            newPaymentline.set_amount(this.get_due());

            if (
                payment_method.payment_terminal ||
                payment_method.payment_method_type === "qr_code"
            ) {
                newPaymentline.set_payment_status("pending");
            }
            return newPaymentline;
        }
    }
    get_paymentlines() {
        return this.paymentlines;
    }
    /**
     * Retrieve the paymentline with the specified cid
     *
     * @param {String} cid
     */
    get_paymentline(cid) {
        var lines = this.get_paymentlines();
        return lines.find(function (line) {
            return line.cid === cid;
        });
    }
    remove_paymentline(line) {
        this.assert_editable();
        if (this.selected_paymentline === line) {
            this.select_paymentline(undefined);
        }
        this.paymentlines = this.paymentlines.filter((l) => l.cid !== line.cid);
    }
    select_paymentline(line) {
        if (line !== this.selected_paymentline) {
            if (this.selected_paymentline) {
                this.selected_paymentline.set_selected(false);
            }
            this.selected_paymentline = line;
            if (this.selected_paymentline) {
                this.selected_paymentline.set_selected(true);
            }
        }
    }
    electronic_payment_in_progress() {
        return this.get_paymentlines().some(function (pl) {
            if (pl.payment_status) {
                return !["done", "reversed"].includes(pl.payment_status);
            } else {
                return false;
            }
        });
    }
    /* ---- Payment Status --- */
    get_subtotal() {
        return round_pr(
            this.orderlines.reduce(function (sum, orderLine) {
                return sum + orderLine.get_display_price();
            }, 0),
            this.pos.currency.rounding
        );
    }
    get_total_with_tax() {
        return this.get_total_without_tax() + this.get_total_tax();
    }
    get_total_without_tax() {
        return round_pr(
            this.orderlines.reduce(function (sum, orderLine) {
                return sum + orderLine.get_price_without_tax();
            }, 0),
            this.pos.currency.rounding
        );
    }
    _get_ignored_product_ids_total_discount() {
        return [];
    }
    get_total_discount() {
        const ignored_product_ids = this._get_ignored_product_ids_total_discount();
        return round_pr(
            this.orderlines.reduce((sum, orderLine) => {
                if (!ignored_product_ids.includes(orderLine.product.id)) {
                    sum +=
                        orderLine.get_all_prices().priceWithTaxBeforeDiscount -
                        orderLine.get_all_prices().priceWithTax;
                    if (
                        orderLine.display_discount_policy() === "without_discount" &&
                        !(orderLine.price_type === "manual")
                    ) {
                        sum +=
                            (orderLine.get_taxed_lst_unit_price() -
                                orderLine.getUnitDisplayPriceBeforeDiscount()) *
                            orderLine.get_quantity();
                    }
                }
                return sum;
            }, 0),
            this.pos.currency.rounding
        );
    }
    get_total_tax() {
        if (this.pos.company.tax_calculation_rounding_method === "round_globally") {
            // As always, we need:
            // 1. For each tax, sum their amount across all order lines
            // 2. Round that result
            // 3. Sum all those rounded amounts
            var groupTaxes = {};
            this.orderlines.forEach(function (line) {
                var taxDetails = line.get_tax_details();
                var taxIds = Object.keys(taxDetails);
                for (var t = 0; t < taxIds.length; t++) {
                    var taxId = taxIds[t];
                    if (!(taxId in groupTaxes)) {
                        groupTaxes[taxId] = 0;
                    }
                    groupTaxes[taxId] += taxDetails[taxId].amount;
                }
            });

            var sum = 0;
            var taxIds = Object.keys(groupTaxes);
            for (var j = 0; j < taxIds.length; j++) {
                var taxAmount = groupTaxes[taxIds[j]];
                sum += round_pr(taxAmount, this.pos.currency.rounding);
            }
            return sum;
        } else {
            return round_pr(
                this.orderlines.reduce(function (sum, orderLine) {
                    return sum + orderLine.get_tax();
                }, 0),
                this.pos.currency.rounding
            );
        }
    }
    get_total_paid() {
        return round_pr(
            this.paymentlines.reduce(function (sum, paymentLine) {
                if (paymentLine.is_done()) {
                    sum += paymentLine.get_amount();
                }
                return sum;
            }, 0),
            this.pos.currency.rounding
        );
    }
    get_tax_details() {
        const taxDetails = {};
        for (const line of this.orderlines) {
            const taxValuesList = line.get_all_prices().taxValuesList;
            for (const taxValues of taxValuesList) {
                const taxId = taxValues.id;
                if (!taxDetails[taxId]) {
                    taxDetails[taxId] = Object.assign({}, taxValues, {
                        amount: 0.0,
                        base: 0.0,
                        display_base: 0.0,
                        tax_percentage: taxValues.amount,
                    });
                }
                taxDetails[taxId].base += taxValues.base;
                taxDetails[taxId].display_base += taxValues.display_base;
                taxDetails[taxId].amount += taxValues.tax_amount_factorized;
            }
        }
        return Object.values(taxDetails);
    }
    get_total_for_taxes(tax_id) {
        var total = 0;

        if (!(tax_id instanceof Array)) {
            tax_id = [tax_id];
        }

        var tax_set = {};

        for (var i = 0; i < tax_id.length; i++) {
            tax_set[tax_id[i]] = true;
        }

        this.orderlines.forEach((line) => {
            var taxes_ids = this.tax_ids || line.get_product().taxes_id;
            for (var i = 0; i < taxes_ids.length; i++) {
                if (tax_set[taxes_ids[i]]) {
                    total += line.get_price_with_tax();
                    return;
                }
            }
        });

        return total;
    }
    get_change(paymentline) {
        if (!paymentline) {
            var change =
                this.get_total_paid() - this.get_total_with_tax() - this.get_rounding_applied();
        } else {
            change = -this.get_total_with_tax();
            var lines = this.paymentlines;
            for (var i = 0; i < lines.length; i++) {
                change += lines[i].get_amount();
                if (lines[i] === paymentline) {
                    break;
                }
            }
        }
        return round_pr(Math.max(0, change), this.pos.currency.rounding);
    }
    get_due(paymentline) {
        if (!paymentline) {
            var due =
                this.get_total_with_tax() - this.get_total_paid() + this.get_rounding_applied();
        } else {
            due = this.get_total_with_tax();
            var lines = this.paymentlines;
            for (var i = 0; i < lines.length; i++) {
                if (lines[i] === paymentline) {
                    break;
                } else {
                    due -= lines[i].get_amount();
                }
            }
        }
        return round_pr(due, this.pos.currency.rounding);
    }
    get_rounding_applied() {
        if (this.pos.config.cash_rounding) {
            const only_cash = this.pos.config.only_round_cash_method;
            const paymentlines = this.get_paymentlines();
            const last_line = paymentlines ? paymentlines[paymentlines.length - 1] : false;
            const last_line_is_cash = last_line
                ? last_line.payment_method.is_cash_count == true
                : false;
            if (!only_cash || (only_cash && last_line_is_cash)) {
                var rounding_method = this.pos.config.rounding_method.rounding_method;
                var remaining = this.get_total_with_tax() - this.get_total_paid();
                var sign = this.get_total_with_tax() > 0 ? 1.0 : -1.0;
                if (
                    ((this.get_total_with_tax() < 0 && remaining > 0) ||
                        (this.get_total_with_tax() > 0 && remaining < 0)) &&
                    rounding_method !== "HALF-UP"
                ) {
                    rounding_method = rounding_method === "UP" ? "DOWN" : "UP";
                }

                remaining *= sign;
                var total = round_pr(remaining, this.pos.config.rounding_method.rounding);
                var rounding_applied = total - remaining;

                // because floor and ceil doesn't include decimals in calculation, we reuse the value of the half-up and adapt it.
                if (floatIsZero(rounding_applied, this.pos.currency.decimal_places)) {
                    // https://xkcd.com/217/
                    return 0;
                } else if (
                    Math.abs(this.get_total_with_tax()) < this.pos.config.rounding_method.rounding
                ) {
                    return 0;
                } else if (rounding_method === "UP" && rounding_applied < 0 && remaining > 0) {
                    rounding_applied += this.pos.config.rounding_method.rounding;
                } else if (rounding_method === "UP" && rounding_applied > 0 && remaining < 0) {
                    rounding_applied -= this.pos.config.rounding_method.rounding;
                } else if (rounding_method === "DOWN" && rounding_applied > 0 && remaining > 0) {
                    rounding_applied -= this.pos.config.rounding_method.rounding;
                } else if (rounding_method === "DOWN" && rounding_applied < 0 && remaining < 0) {
                    rounding_applied += this.pos.config.rounding_method.rounding;
                } else if (
                    rounding_method === "HALF-UP" &&
                    rounding_applied === this.pos.config.rounding_method.rounding / -2
                ) {
                    rounding_applied += this.pos.config.rounding_method.rounding;
                }
                return sign * rounding_applied;
            } else {
                return 0;
            }
        }
        return 0;
    }
    has_not_valid_rounding() {
        if (
            !this.pos.config.rounding_method ||
            this.get_total_with_tax() < this.pos.config.rounding_method.rounding
        ) {
            return false;
        }

        const only_cash = this.pos.config.only_round_cash_method;
        var lines = this.paymentlines;

        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            if (only_cash && !line.payment_method.is_cash_count) {
                continue;
            }

            if (
                !floatIsZero(
                    line.amount - round_pr(line.amount, this.pos.config.rounding_method.rounding),
                    6
                )
            ) {
                return line;
            }
        }
        return false;
    }
    is_paid() {
        return this.get_due() <= 0;
    }
    is_paid_with_cash() {
        return !!this.paymentlines.find(function (pl) {
            return pl.payment_method.is_cash_count;
        });
    }
    check_paymentlines_rounding() {
        if (this.pos.config.cash_rounding) {
            var cash_rounding = this.pos.config.rounding_method.rounding;
            var default_rounding = this.pos.currency.rounding;
            for (var id in this.get_paymentlines()) {
                var line = this.get_paymentlines()[id];
                var diff = round_pr(
                    round_pr(line.amount, cash_rounding) - round_pr(line.amount, default_rounding),
                    default_rounding
                );
                if (this.get_total_with_tax() < this.pos.config.rounding_method.rounding) {
                    return true;
                }
                if (diff && line.payment_method.is_cash_count) {
                    return false;
                } else if (!this.pos.config.only_round_cash_method && diff) {
                    return false;
                }
            }
            return true;
        }
        return true;
    }
    get_total_cost() {
        return this.orderlines.reduce(function (sum, orderLine) {
            return sum + orderLine.get_total_cost();
        }, 0);
    }
    /* ---- Invoice --- */
    set_to_invoice(to_invoice) {
        this.assert_editable();
        this.to_invoice = to_invoice;
    }
    is_to_invoice() {
        return this.to_invoice;
    }
    /* ---- Partner --- */
    // the partner related to the current order.
    set_partner(partner) {
        this.assert_editable();
        this.partner = partner;
        this.updatePricelistAndFiscalPosition(partner);
    }
    get_partner() {
        return this.partner;
    }
    get_partner_name() {
        const partner = this.partner;
        return partner ? partner.name : "";
    }
    get_cardholder_name() {
        var card_payment_line = this.paymentlines.find((pl) => pl.cardholder_name);
        return card_payment_line ? card_payment_line.cardholder_name : "";
    }
    /* ---- Screen Status --- */
    // the order also stores the screen status, as the PoS supports
    // different active screens per order. This method is used to
    // store the screen status.
    set_screen_data(value) {
        this.screen_data["value"] = value;
    }
    get_current_screen_data() {
        return this.screen_data["value"] ?? { name: "ProductScreen" };
    }
    //see set_screen_data
    get_screen_data() {
        const screen = this.screen_data["value"];
        // If no screen data is saved
        //   no payment line -> product screen
        //   with payment line -> payment screen
        if (!screen) {
            if (this.get_paymentlines().length > 0) {
                return { name: "PaymentScreen" };
            }
            return { name: "ProductScreen" };
        }
        if (!this.finalized && this.get_paymentlines().length > 0) {
            return { name: "PaymentScreen" };
        }
        return screen;
    }
    wait_for_push_order() {
        return false;
    }
    updatePricelistAndFiscalPosition(newPartner) {
        let newPartnerPricelist, newPartnerFiscalPositionId;
        const defaultFiscalPositionId = this.pos.config.default_fiscal_position_id?.id;
        if (newPartner) {
            newPartnerFiscalPositionId =
                newPartner.property_account_position_id?.id || defaultFiscalPositionId;
            newPartnerPricelist =
                this.pos.models["product.pricelist"].find(
                    (pricelist) => pricelist.id === newPartner.property_product_pricelist?.id
                ) || this.pos.config.pricelist_id;
        } else {
            newPartnerFiscalPositionId = defaultFiscalPositionId;
            newPartnerPricelist = this.pos.config.pricelist_id;
        }
        const fiscalPosition = this.pos.models["account.fiscal.position"].find(
            (fp) => fp.id === newPartnerFiscalPositionId
        );
        this.set_fiscal_position(fiscalPosition);
        this.set_pricelist(newPartnerPricelist);
    }
    /* ---- Ship later --- */
    setShippingDate(shippingDate) {
        this.shippingDate = shippingDate;
    }
    getShippingDate() {
        return this.shippingDate;
    }
    getHasRefundLines() {
        for (const line of this.get_orderlines()) {
            if (line.refunded_orderline_id) {
                return true;
            }
        }
        return false;
    }
    /**
     * Returns false if the current order is empty and has no payments.
     * @returns {boolean}
     */
    _isValidEmptyOrder() {
        if (this.get_orderlines().length == 0) {
            return this.get_paymentlines().length != 0;
        } else {
            return true;
        }
    }
    _generateTicketCode() {
        return random5Chars();
    }
    _getOrderOptions() {
        return {};
    }
}
