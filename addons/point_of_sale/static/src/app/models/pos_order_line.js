import { registry } from "@web/core/registry";
import { constructFullProductName, uuidv4 } from "@point_of_sale/utils";
import { Base } from "./related_models";
import { parseFloat } from "@web/views/fields/parsers";
import { formatFloat, roundDecimals, roundPrecision, floatIsZero } from "@web/core/utils/numbers";
import { roundCurrency, formatCurrency } from "./utils/currency";
import { _t } from "@web/core/l10n/translation";
import { localization as l10n } from "@web/core/l10n/localization";

import {
    getTaxesAfterFiscalPosition,
    getTaxesValues,
} from "@point_of_sale/app/models/utils/tax_utils";

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
        this.setFullProductName();

        // Data that are not saved in the backend
        this.uiState = {
            hasChange: true,
        };
    }

    setFullProductName() {
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
                this.setQuantity(code.value);
            } else if (code.type === "price") {
                this.setUnitPrice(code.value);
                this.price_type = "manual";
            }

            if (product_packaging_by_barcode[code.code]) {
                this.setQuantity(product_packaging_by_barcode[code.code].qty);
            }
        }

        this.setUnitPrice(this.price_unit);
    }

    get preparationKey() {
        const note = this.getNote();
        return `${this.uuid} - ${note}`;
    }

    get quantityStr() {
        let unitPart = "";
        let decimalPart = "";
        const unit = this.product_id.uom_id;
        const decimalPoint = l10n.decimalPoint;

        if (unit) {
            if (unit.rounding) {
                const decimals = this.models["decimal.precision"].find(
                    (dp) => dp.name === "Product Unit of Measure"
                ).digits;

                if (this.qty % 1 === 0) {
                    unitPart = this.qty.toFixed(0);
                } else {
                    const formatted = formatFloat(this.qty, { digits: [69, decimals] });
                    const parts = formatted.split(decimalPoint);
                    unitPart = parts[0] + decimalPoint;
                    decimalPart = parts[1] || "";
                }
            } else {
                unitPart = this.qty.toFixed(0);
            }
        } else {
            unitPart = "" + this.qty;
        }
        return {
            qtyStr: unitPart + (decimalPart ? decimalPoint + decimalPart : ""),
            unitPart: unitPart,
            decimalPart: decimalPart,
        };
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
        this.order_id.selectOrderline(this);
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
            this.setQuantityByLot();
        }
        this.setDirty();
    }

    setDiscount(discount) {
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
        const prices = this.getAllPrices();
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
    setQuantity(quantity, keep_price) {
        if (this.order_id.preset_id?.is_return) {
            quantity = -Math.abs(quantity);
        }

        this.order_id.assertEditable();
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
            const productTemplate = this.product_id.product_tmpl_id;
            this.setUnitPrice(
                productTemplate.getPrice(
                    this.order_id.pricelist_id,
                    this.getQuantity(),
                    this.getPriceExtra(),
                    false,
                    this.product_id
                )
            );
        }

        this.setDirty();
        return true;
    }

    setQuantityByLot() {
        var valid_lots_quantity = this.getValidLots().length;
        if (this.qty < 0) {
            valid_lots_quantity = -valid_lots_quantity;
        }
        this.setQuantity(valid_lots_quantity);
    }

    hasValidProductLot() {
        if (this.pack_lot_ids.length > 0) {
            return true;
        }

        const valid_product_lot = this.getValidLots();
        const lotsRequired = this.product_id.tracking == "serial" ? Math.abs(this.qty) : 1;
        return lotsRequired === valid_product_lot.length;
    }

    canBeMergedWith(orderline) {
        const productPriceUnit = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        ).digits;
        const price = window.parseFloat(
            roundDecimals(this.price_unit || 0, productPriceUnit).toFixed(productPriceUnit)
        );
        const product = orderline.getProduct();
        let order_line_price = product.getPrice(
            orderline.order_id.pricelist_id,
            this.getQuantity(),
            0,
            false,
            product
        );
        order_line_price = roundDecimals(order_line_price, this.currency.decimal_places);

        const isSameCustomerNote =
            (Boolean(orderline.getCustomerNote()) === false &&
                Boolean(this.getCustomerNote()) === false) ||
            orderline.getCustomerNote() === this.getCustomerNote();

        // only orderlines of the same product can be merged
        return (
            !this.skip_change &&
            orderline.getNote() === this.getNote() &&
            this.getProduct().id === orderline.getProduct().id &&
            this.isPosGroupable() &&
            // don't merge discounted orderlines
            this.getDiscount() === 0 &&
            floatIsZero(price - order_line_price - orderline.getPriceExtra(), this.currency) &&
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

    isPosGroupable() {
        const unit_groupable = this.product_id.uom_id
            ? this.product_id.uom_id.is_pos_groupable
            : false;
        return unit_groupable && !this.isPartOfCombo();
    }

    merge(orderline) {
        this.order_id.assertEditable();
        this.setQuantity(this.getQuantity() + orderline.getQuantity());
        this.update({
            pack_lot_ids: [["link", ...orderline.pack_lot_ids]],
        });
    }

    setUnitPrice(price) {
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

    getUnitPrice() {
        const digits = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        ).digits;
        // round and truncate to mimic _symbol_set behavior
        return window.parseFloat(roundDecimals(this.price_unit || 0, digits).toFixed(digits));
    }

    get unitDisplayPrice() {
        const prices =
            this.combo_line_ids.length > 0
                ? this.combo_line_ids.reduce(
                      (acc, cl) => ({
                          priceWithTax: acc.priceWithTax + cl.allUnitPrices.priceWithTax,
                          priceWithoutTax: acc.priceWithoutTax + cl.allUnitPrices.priceWithoutTax,
                      }),
                      { priceWithTax: 0, priceWithoutTax: 0 }
                  )
                : this.allUnitPrices;

        return this.config.iface_tax_included === "total"
            ? prices.priceWithTax
            : prices.priceWithoutTax;
    }

    getUnitDisplayPriceBeforeDiscount() {
        if (this.config.iface_tax_included === "total") {
            return this.allUnitPrices.priceWithTaxBeforeDiscount;
        } else {
            return this.allUnitPrices.priceWithoutTaxBeforeDiscount;
        }
    }
    getBasePrice() {
        const rounding = this.currency.rounding;

        return roundPrecision(
            this.getUnitPrice() * this.getQuantity() * (1 - this.getDiscount() / 100),
            rounding
        );
    }

    getDisplayPrice() {
        if (this.config.iface_tax_included === "total") {
            return this.getPriceWithTax();
        } else {
            return this.getPriceWithoutTax();
        }
    }

    getTaxedlstUnitPrice() {
        const priceUnit = this.getlstPrice();
        const product = this.getProduct();

        let taxes = product.taxes_id;

        // Fiscal position.
        const order = this.order_id;
        if (order.fiscal_position_id) {
            taxes = getTaxesAfterFiscalPosition(taxes, order.fiscal_position_id, this.models);
        }

        const taxesData = getTaxesValues(
            taxes,
            priceUnit,
            1,
            product,
            this.config._product_default_values,
            this.company,
            this.currency
        );
        if (this.config.iface_tax_included === "total") {
            return taxesData.total_included;
        } else {
            return taxesData.total_excluded;
        }
    }

    getPriceWithoutTax() {
        return this.allPrices.priceWithoutTax;
    }

    getPriceWithTax() {
        return this.allPrices.priceWithTax;
    }

    getTax() {
        return this.allPrices.tax;
    }

    getTaxDetails() {
        return this.allPrices.taxDetails;
    }

    getTotalTaxesIncludedInPrice() {
        const productTaxes = this._getProductTaxesAfterFiscalPosition();
        const taxDetails = this.getTaxDetails();
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
        const product = this.getProduct();
        let taxes = this.tax_ids || product.taxes_id;

        // Fiscal position.
        const fiscalPosition = this.order_id.fiscal_position_id;
        if (fiscalPosition) {
            taxes = getTaxesAfterFiscalPosition(taxes, fiscalPosition, this.models);
        }

        return taxes;
    }

    getAllPrices(qty = this.getQuantity()) {
        const product = this.getProduct();
        const priceUnit = this.getUnitPrice();
        const discount = this.getDiscount();
        const priceUnitAfterDiscount = priceUnit * (1.0 - discount / 100.0);

        let taxes = this.tax_ids || product.taxes_id;

        // Fiscal position.
        const fiscalPosition = this.order_id.fiscal_position_id;
        if (fiscalPosition) {
            taxes = getTaxesAfterFiscalPosition(taxes, fiscalPosition, this.models);
        }

        const taxesData = getTaxesValues(
            taxes,
            priceUnitAfterDiscount,
            qty,
            product,
            this.config._product_default_values,
            this.company,
            this.currency
        );
        const taxesDataBeforeDiscount = getTaxesValues(
            taxes,
            priceUnit,
            qty,
            product,
            this.config._product_default_values,
            this.company,
            this.currency
        );

        // Tax details.
        const taxDetails = {};
        for (const taxData of taxesData.taxes_data) {
            taxDetails[taxData.id] = {
                amount: taxData.tax_amount,
                base: taxData.base,
            };
        }

        return {
            priceWithTax: taxesData.total_included,
            priceWithoutTax: taxesData.total_excluded,
            priceWithTaxBeforeDiscount: taxesDataBeforeDiscount.total_included,
            priceWithoutTaxBeforeDiscount: taxesDataBeforeDiscount.total_excluded,
            tax: taxesData.total_included - taxesData.total_excluded,
            taxDetails: taxDetails,
            taxesData: taxesData.taxes_data,
        };
    }

    get allPrices() {
        return this.getAllPrices();
    }

    get allUnitPrices() {
        return this.getAllPrices(1);
    }

    displayDiscountPolicy() {
        // Sales dropped `discount_policy`, and we only show discount if applied pricelist rule
        // is a percentage discount. However we don't have that information in pos
        // so this is heuristic used to imitate the same behavior.
        if (
            this.order_id.pricelist_id &&
            this.order_id.pricelist_id.item_ids
                .map((rule) => rule.compute_price)
                .includes("percentage")
        ) {
            return "without_discount";
        }
        return "with_discount";
    }

    getlstPrice() {
        return this.product_id.getPrice(
            this.config.pricelist_id,
            1,
            this.price_extra,
            false,
            this.product_id
        );
    }

    setCustomerNote(note) {
        this.customer_note = note || "";
        this.setDirty();
    }

    getCustomerNote() {
        return this.customer_note;
    }

    getTotalCost() {
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
        return allLines.reduce((total, line) => total + line.allUnitPrices.priceWithTax, 0);
    }
    getComboTotalPriceWithoutTax() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((total, line) => total + line.getBasePrice() / line.qty, 0);
    }

    getOldUnitDisplayPrice() {
        return (
            this.displayDiscountPolicy() === "without_discount" &&
            roundCurrency(this.unitDisplayPrice, this.currency) <
                roundCurrency(this.getTaxedlstUnitPrice(), this.currency) &&
            this.getTaxedlstUnitPrice()
        );
    }

    getPriceString() {
        return this.getDiscountStr() === "100"
            ? // free if the discount is 100
              _t("Free")
            : this.combo_line_ids.length > 0
            ? // total of all combo lines if it is combo parent
              formatCurrency(
                  this.combo_line_ids.reduce((total, cl) => total + cl.getDisplayPrice(), 0),
                  this.currency
              )
            : this.combo_parent_id
            ? // empty string if it has combo parent
              ""
            : formatCurrency(this.getDisplayPrice(), this.currency);
    }

    get packLotLines() {
        return this.pack_lot_ids.map(
            (l) =>
                `${l.pos_order_line_id.product_id.tracking == "lot" ? "Lot Number" : "SN"} ${
                    l.lot_name
                }`
        );
    }

    get taxGroupLabels() {
        return [
            ...new Set(
                this.product_id.taxes_id
                    ?.map((tax) => tax.tax_group_id.pos_receipt_label)
                    .filter((label) => label)
            ),
        ].join(" ");
    }

    getDiscount() {
        return this.discount || 0;
    }

    // FIXME all below should be removed
    getValidLots() {
        return this.pack_lot_ids.filter((item) => item.lot_name);
    }
    // FIXME what is the use of this ?
    updateSavedQuantity() {
        this.saved_quantity = this.qty;
    }
    getPriceExtra() {
        return this.price_extra;
    }
    setPriceExtra(price_extra) {
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
    getDiscountStr() {
        return this.discount ? this.discount.toString() : "";
    }
    getQuantity() {
        return this.qty;
    }
    getQuantityStr() {
        return this.quantityStr;
    }
    getUnit() {
        return this.product_id.uom_id;
    }
    // return the product of this orderline
    getProduct() {
        return this.product_id;
    }
    getFullProductName() {
        return this.full_product_name || this.product_id.display_name;
    }
    isSelected() {
        return this.order_id?.uiState?.selected_orderline_uuid === this.uuid;
    }
}

registry.category("pos_available_models").add(PosOrderline.pythonModel, PosOrderline);
