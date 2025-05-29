import { registry } from "@web/core/registry";
import { constructFullProductName, uuidv4 } from "@point_of_sale/utils";
import { Base } from "./related_models";
import { parseFloat } from "@web/views/fields/parsers";
import { formatFloat, roundDecimals, roundPrecision, floatIsZero } from "@web/core/utils/numbers";
import { roundCurrency, formatCurrency } from "./utils/currency";
import { _t } from "@web/core/l10n/translation";
import { getTaxesAfterFiscalPosition } from "@point_of_sale/app/models/utils/tax_utils";
import { accountTaxHelpers } from "@account/helpers/account_tax";

export class PosOrderline extends Base {
    static pythonModel = "pos.order.line";

    setup(vals) {
        super.setup(vals);
        if (!this.product_id) {
            this.delete();
            return;
        }
        this.uuid = vals.uuid ? vals.uuid : uuidv4();
        this.skip_change = vals.skip_change || false;
        this.set_full_product_name();

        // Data that are not saved in the backend
        this.uiState = {
            hasChange: true,
        };
        this.saved_quantity = 0;
    }

    set_full_product_name() {
        this.full_product_name = constructFullProductName(this);
    }

    setOptions(options) {
        if (options.uiState) {
            this.uiState = { ...this.uiState, ...options.uiState };
        }

        if (options.code) {
            const code = options.code;
            const blockMerge = ["weight", "quantity", "discount"];
            const product_packaging_by_barcode =
                this.models["product.packaging"].getAllBy("barcode");

            if (blockMerge.includes(code.type)) {
                this.set_quantity(code.value);
            } else if (code.type === "price") {
                this.set_unit_price(code.value);
                this.price_type = "manual";
            }

            if (product_packaging_by_barcode[code.code]) {
                this.set_quantity(product_packaging_by_barcode[code.code].qty);
            }
        }

        this.set_unit_price(this.price_unit);
    }

    get preparationKey() {
        return this.uuid;
    }

    get quantityStr() {
        let qtyStr = "";
        const unit = this.product_id.uom_id;

        if (unit) {
            if (unit.rounding) {
                const decimals = this.models["decimal.precision"].find(
                    (dp) => dp.name === "Product Unit of Measure"
                ).digits;
                qtyStr = formatFloat(this.qty, {
                    digits: [69, decimals],
                });
            } else {
                qtyStr = this.qty.toFixed(0);
            }
        } else {
            qtyStr = "" + this.qty;
        }

        return qtyStr;
    }

    get company() {
        return this.models["res.company"].getFirst();
    }

    get config() {
        return this.models["pos.config"].getFirst();
    }

    get session() {
        return this.models["pos.session"].getFirst();
    }

    get currency() {
        return this.order_id.currency;
    }

    get pickingType() {
        return this.models["stock.picking.type"].getFirst();
    }

    // To be overrided
    getDisplayClasses() {
        return {};
    }

    getPackLotLinesToEdit(isAllowOnlyOneLot) {
        const currentPackLotLines = this.pack_lot_ids;
        let nExtraLines = Math.abs(this.qty) - currentPackLotLines.length;
        nExtraLines = Math.ceil(nExtraLines);
        nExtraLines = nExtraLines > 0 ? nExtraLines : 1;
        const tempLines = currentPackLotLines
            .map((lotLine) => ({
                id: lotLine.id,
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
    async editPackLotLines(editedPackLotLines) {
        if (!editedPackLotLines) {
            return;
        }
        this.setPackLotLines(editedPackLotLines);
        this.order_id.select_orderline(this);
    }

    setPackLotLines({ modifiedPackLotLines, newPackLotLines, setQuantity = true }) {
        const lotLinesToRemove = [];

        for (const lotLine of this.pack_lot_ids) {
            const modifiedLotName = modifiedPackLotLines[lotLine.id];
            if (modifiedLotName) {
                lotLine.lot_name = modifiedLotName;
            } else {
                lotLinesToRemove.push(lotLine);
            }
        }

        // Remove those that needed to be removed.
        for (const lotLine of lotLinesToRemove) {
            this.pack_lot_ids = this.pack_lot_ids.filter((pll) => pll.id !== lotLine.id);
        }

        for (const newLotLine of newPackLotLines) {
            this.models["pos.pack.operation.lot"].create({
                lot_name: newLotLine.lot_name,
                pos_order_line_id: this,
            });
        }

        // Set the qty of the line based on number of pack lots.
        if (!this.product_id.to_weight && setQuantity) {
            this.set_quantity_by_lot();
        }
        this.setDirty();
    }

    // FIXME related models update stuff
    set_product_lot(product) {
        this.has_product_lot = product.tracking !== "none";
        this.pack_lot_ids = this.has_product_lot && [];
        this.setDirty();
    }

    set_discount(discount) {
        const parsed_discount =
            typeof discount === "number"
                ? discount
                : isNaN(parseFloat(discount))
                ? 0
                : parseFloat("" + discount);

        const disc = Math.min(Math.max(parsed_discount || 0, 0), 100);
        this.discount = disc;
        this.order_id.recomputeOrderData();
        this.setDirty();
    }

    setLinePrice() {
        const prices = this.get_all_prices();
        if (this.price_subtotal !== prices.priceWithoutTax) {
            this.price_subtotal = prices.priceWithoutTax;
        }
        if (this.price_subtotal_incl !== prices.priceWithTax) {
            this.price_subtotal_incl = prices.priceWithTax;
        }
    }

    // sets the qty of the product. The qty will be rounded according to the
    // product's unity of measure properties. Quantities greater than zero will not get
    // rounded to zero
    set_quantity(quantity, keep_price) {
        this.order_id.assert_editable();
        const quant =
            typeof quantity === "number" ? quantity : parseFloat("" + (quantity ? quantity : 0));

        const allLineToRefundUuids = this.models["pos.order"].reduce((acc, order) => {
            Object.assign(acc, order.uiState.lineToRefund);
            return acc;
        }, {});

        if (this.refunded_orderline_id?.uuid in allLineToRefundUuids) {
            const refundDetails = allLineToRefundUuids[this.refunded_orderline_id.uuid];
            const maxQtyToRefund = refundDetails.line.qty - refundDetails.line.refunded_qty;
            if (quant > 0) {
                return {
                    title: _t("Positive quantity not allowed"),
                    body: _t(
                        "Only a negative quantity is allowed for this refund line. Click on +/- to modify the quantity to be refunded."
                    ),
                };
            } else if (quant == 0) {
                refundDetails.qty = 0;
            } else if (-quant <= maxQtyToRefund) {
                refundDetails.qty = -quant;
            } else {
                return {
                    title: _t("Greater than allowed"),
                    body: _t(
                        "The requested quantity to be refunded is higher than the refundable quantity."
                    ),
                };
            }
        }
        const unit = this.product_id.uom_id;
        if (unit) {
            if (unit.rounding) {
                const decimals = this.models["decimal.precision"].find(
                    (dp) => dp.name === "Product Unit of Measure"
                ).digits;
                const rounding = Math.max(unit.rounding, Math.pow(10, -decimals));
                this.qty = roundPrecision(quant, rounding);
            } else {
                this.qty = roundPrecision(quant, 1);
            }
        } else {
            this.qty = quant;
        }

        // just like in sale.order changing the qty will recompute the unit price
        if (!keep_price && this.price_type === "original") {
            this.set_unit_price(
                this.product_id.get_price(
                    this.order_id.pricelist_id,
                    this.get_quantity(),
                    this.get_price_extra()
                )
            );
        }

        this.setDirty();
        return true;
    }

    get_quantity_str_with_unit() {
        const unit = this.product_id.uom_id;
        if (this.is_pos_groupable()) {
            return this.quantityStr + " " + unit.name;
        } else {
            return this.quantityStr;
        }
    }

    get_required_number_of_lots() {
        var lots_required = 1;

        if (this.product_id.tracking == "serial") {
            lots_required = Math.abs(this.qty);
        }

        return lots_required;
    }

    set_quantity_by_lot() {
        var valid_lots_quantity = this.get_valid_lots().length;
        if (this.qty < 0) {
            valid_lots_quantity = -valid_lots_quantity;
        }
        this.set_quantity(valid_lots_quantity);
    }

    has_valid_product_lot() {
        if (this.pack_lot_ids.length > 0) {
            return true;
        }

        const valid_product_lot = this.get_valid_lots();
        return this.get_required_number_of_lots() === valid_product_lot.length;
    }

    can_be_merged_with(orderline) {
        const productPriceUnit = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        ).digits;
        const price = window.parseFloat(
            roundDecimals(this.price_unit || 0, productPriceUnit).toFixed(productPriceUnit)
        );
        let order_line_price = orderline
            .get_product()
            .get_price(orderline.order_id.pricelist_id, this.get_quantity());
        order_line_price = roundDecimals(order_line_price, this.currency.decimal_places);

        const isSameCustomerNote =
            (Boolean(orderline.get_customer_note()) === false &&
                Boolean(this.get_customer_note()) === false) ||
            orderline.get_customer_note() === this.get_customer_note();

        // only orderlines of the same product can be merged
        return (
            !this.skip_change &&
            orderline.getNote() === this.getNote() &&
            this.get_product().id === orderline.get_product().id &&
            this.is_pos_groupable() &&
            // don't merge discounted orderlines
            this.get_discount() === 0 &&
            floatIsZero(
                price - order_line_price - orderline.get_price_extra(),
                this.currency.decimal_places
            ) &&
            !this.isLotTracked() &&
            this.full_product_name === orderline.full_product_name &&
            isSameCustomerNote &&
            !this.refunded_orderline_id &&
            !orderline.isPartOfCombo()
        );
    }

    isLotTracked() {
        return (
            this.product_id.tracking === "lot" &&
            (this.pickingType.use_create_lots || this.pickingType.use_existing_lots)
        );
    }

    is_pos_groupable() {
        const unit_groupable = this.product_id.uom_id
            ? this.product_id.uom_id.is_pos_groupable
            : false;
        return unit_groupable && !this.isPartOfCombo();
    }

    merge(orderline) {
        this.order_id.assert_editable();
        this.set_quantity(this.get_quantity() + orderline.get_quantity());
        this.update({
            pack_lot_ids: [["link", ...orderline.pack_lot_ids]],
        });
    }

    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const order = this.order_id;
        const currency = order.config.currency_id;
        const extraValues = { currency_id: currency };
        const product = this.get_product();
        const priceUnit = this.get_unit_price();
        const discount = this.get_discount();

        const values = {
            ...extraValues,
            quantity: this.qty,
            price_unit: priceUnit,
            discount: discount,
            tax_ids: this.tax_ids,
            product_id: accountTaxHelpers.eval_taxes_computation_prepare_product_values(
                this.config._product_default_values,
                product
            ),
            ...customValues,
        };
        if (order.fiscal_position_id) {
            values.tax_ids = getTaxesAfterFiscalPosition(
                values.tax_ids,
                order.fiscal_position_id,
                order.models
            );
        }
        return values;
    }

    set_unit_price(price) {
        const parsed_price = !isNaN(price)
            ? price
            : isNaN(parseFloat(price))
            ? 0
            : parseFloat("" + price);
        this.price_unit = roundDecimals(
            parsed_price || 0,
            this.models["decimal.precision"].find((dp) => dp.name === "Product Price").digits
        );
        this.setDirty();
    }

    get_unit_price() {
        const digits = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        ).digits;
        // round and truncate to mimic _symbol_set behavior
        return window.parseFloat(roundDecimals(this.price_unit || 0, digits).toFixed(digits));
    }

    get_unit_display_price() {
        if (this.config.iface_tax_included === "total") {
            return this.get_all_prices(1).priceWithTax;
        } else {
            return this.get_all_prices(1).priceWithoutTax;
        }
    }

    getUnitDisplayPriceBeforeDiscount() {
        if (this.config.iface_tax_included === "total") {
            return this.get_all_prices(1).priceWithTaxBeforeDiscount;
        } else {
            return this.get_all_prices(1).priceWithoutTaxBeforeDiscount;
        }
    }
    get_base_price() {
        const rounding = this.currency.rounding;

        return roundPrecision(
            this.get_unit_price() * this.get_quantity() * (1 - this.get_discount() / 100),
            rounding
        );
    }

    get_display_price() {
        if (this.config.iface_tax_included === "total") {
            return this.get_price_with_tax();
        } else {
            return this.get_price_without_tax();
        }
    }

    get_taxed_lst_unit_price() {
        const company = this.company;
        const product = this.get_product();
        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues({
                price_unit: this.get_lst_price(),
                quantity: 1,
                tax_ids: product.taxes_id,
            })
        );
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, company);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], company);
        const taxDetails = baseLine.tax_details;

        if (this.config.iface_tax_included === "total") {
            return taxDetails.total_included_currency;
        } else {
            return taxDetails.total_excluded_currency;
        }
    }

    get_price_without_tax() {
        return this.get_all_prices().priceWithoutTax;
    }

    get_price_with_tax() {
        return this.get_all_prices().priceWithTax;
    }

    get_price_with_tax_before_discount() {
        return this.get_all_prices().priceWithTaxBeforeDiscount;
    }

    get_tax() {
        return this.get_all_prices().tax;
    }

    get_tax_details() {
        return this.get_all_prices().taxDetails;
    }

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
        const baseLineValues = this.prepareBaseLineForTaxesComputationExtraValues();
        return baseLineValues.tax_ids;
    }

    get_all_prices(qty = this.get_quantity()) {
        const company = this.company;
        const product = this.get_product();
        const taxes = this.tax_ids || product.taxes_id;
        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues({
                quantity: qty,
                tax_ids: taxes,
            })
        );
        accountTaxHelpers.add_tax_details_in_base_line(baseLine, company);
        accountTaxHelpers.round_base_lines_tax_details([baseLine], company);

        const baseLineNoDiscount = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues({
                quantity: qty,
                tax_ids: taxes,
                discount: 0.0,
            })
        );
        accountTaxHelpers.add_tax_details_in_base_line(baseLineNoDiscount, company);
        accountTaxHelpers.round_base_lines_tax_details([baseLineNoDiscount], company);

        // Tax details.
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
            tax:
                baseLine.tax_details.total_included_currency -
                baseLine.tax_details.total_excluded_currency,
            taxDetails: taxDetails,
            taxesData: baseLine.tax_details.taxes_data,
        };
    }

    display_discount_policy() {
        // Sales dropped `discount_policy`, and we only show discount if applied pricelist rule
        // is a percentage discount.
        const pricelistRule = this.product_id.getPricelistRule(
            this.order_id.pricelist_id,
            this.get_quantity()
        );
        if (pricelistRule && pricelistRule.compute_price === "percentage") {
            return "without_discount";
        }
        return "with_discount";
    }

    get_lst_price() {
        return this.product_id.get_price(this.config.pricelist_id, 1, this.price_extra);
    }

    is_last_line() {
        const order = this.order_id;
        const orderlines = order.lines;
        const last_id = orderlines[orderlines.length - 1].uuid;
        const selectedLine = order ? order.get_selected_orderline() : null;

        return !selectedLine ? false : last_id === selectedLine.uuid;
    }

    set_customer_note(note) {
        this.customer_note = note || "";
        this.setDirty();
    }

    get_customer_note() {
        return this.customer_note;
    }

    get_total_cost() {
        return this.product_id.standard_price * this.qty;
    }

    isTipLine() {
        const tipProduct = this.config.tip_product_id;
        return tipProduct && this.product_id.id === tipProduct.id;
    }

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
        return allLines.reduce((total, line) => total + line.get_base_price() / line.qty, 0);
    }

    get_old_unit_display_price() {
        return (
            this.display_discount_policy() === "without_discount" &&
            roundCurrency(this.get_unit_display_price(), this.currency) <
                roundCurrency(this.get_taxed_lst_unit_price(), this.currency) &&
            this.get_taxed_lst_unit_price()
        );
    }

    getPriceString() {
        return this.get_discount_str() === "100"
            ? // free if the discount is 100
              _t("Free")
            : this.combo_line_ids.length > 0
            ? // empty string if it is a combo parent line
              ""
            : formatCurrency(this.get_display_price(), this.currency);
    }

    getDisplayData() {
        return {
            productName: this.get_full_product_name(),
            price: this.getPriceString(),
            qty: this.get_quantity_str(),
            unit: this.product_id.uom_id ? this.product_id.uom_id.name : "",
            unitPrice: formatCurrency(this.get_unit_display_price(), this.currency),
            oldUnitPrice: this.get_old_unit_display_price()
                ? formatCurrency(this.get_old_unit_display_price(), this.currency)
                : "",
            discount: this.get_discount_str(),
            customerNote: this.get_customer_note() || "",
            internalNote: this.getNote(),
            comboParent: this.combo_parent_id?.get_full_product_name?.() || "",
            packLotLines: this.pack_lot_ids.map(
                (l) =>
                    `${l.pos_order_line_id.product_id.tracking == "lot" ? "Lot Number" : "SN"} ${
                        l.lot_name
                    }`
            ),
            price_without_discount: formatCurrency(
                this.getUnitDisplayPriceBeforeDiscount(),
                this.currency
            ),
            taxGroupLabels: [
                ...new Set(
                    getTaxesAfterFiscalPosition(
                        this.product_id.taxes_id,
                        this.order_id.fiscal_position_id,
                        this.models
                    )
                        ?.map((tax) => tax.tax_group_id.pos_receipt_label)
                        .filter((label) => label)
                ),
            ].join(" "),
        };
    }

    get_discount() {
        return this.discount || 0;
    }

    // FIXME all below should be removed
    get_valid_lots() {
        return this.pack_lot_ids.filter((item) => {
            return item.lot_name;
        });
    }
    // FIXME what is the use of this ?
    updateSavedQuantity() {
        this.saved_quantity = this.qty;
    }
    get_price_extra() {
        return this.price_extra;
    }
    set_price_extra(price_extra) {
        this.price_extra = parseFloat(price_extra) || 0.0;
    }
    getNote() {
        return this.note || "";
    }
    setNote(note) {
        this.setDirty();
        this.note = note;
    }
    setHasChange(isChange) {
        this.uiState.hasChange = isChange;
    }
    get_discount_str() {
        return this.discount ? this.discount.toString() : "";
    }
    get_quantity() {
        return this.qty;
    }
    get_quantity_str() {
        return this.quantityStr;
    }
    get_unit() {
        return this.product_id.uom_id;
    }
    // return the product of this orderline
    get_product() {
        return this.product_id;
    }
    get_full_product_name() {
        return this.full_product_name || this.product_id.display_name;
    }
    isSelected() {
        return this.order_id?.uiState?.selected_orderline_uuid === this.uuid;
    }
}

registry.category("pos_available_models").add(PosOrderline.pythonModel, PosOrderline);
