import { registry } from "@web/core/registry";
import { constructFullProductName, constructAttributeString } from "@point_of_sale/utils";
import { Base } from "./related_models";
import { parseFloat } from "@web/views/fields/parsers";
import { formatFloat } from "@web/core/utils/numbers";
import { formatCurrency } from "./utils/currency";
import { _t } from "@web/core/l10n/translation";
import { localization as l10n } from "@web/core/l10n/localization";
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
        this.setFullProductName();
    }

    initState() {
        super.initState();
        // Data that are not saved in the backend
        this.uiState = {
            hasChange: true,
            savedQuantity: 0,
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
            const product_packaging_by_barcode = this.models["product.uom"].getAllBy("barcode");
            const uom_by_id = this.models["uom.uom"].getAllBy("id");

            if (blockMerge.includes(code.type)) {
                this.setQuantity(code.value);
            } else if (code.type === "price") {
                this.setUnitPrice(code.value);
                this.price_type = "manual";
            }

            if (product_packaging_by_barcode[code.code]) {
                this.setQuantity(
                    uom_by_id[product_packaging_by_barcode[code.code].uom_id.id].factor /
                        this.product_id.product_tmpl_id.uom_id.factor
                );
            }
        }

        this.setUnitPrice(this.price_unit);
    }

    get preparationKey() {
        return this.uuid;
    }

    get quantityStr() {
        let unitPart = "";
        let decimalPart = "";
        const unit = this.product_id.uom_id;
        const decimalPoint = l10n.decimalPoint;

        if (unit) {
            if (unit.rounding) {
                const ProductUnit = this.models["decimal.precision"].find(
                    (dp) => dp.name === "Product Unit"
                );

                if (this.qty % 1 === 0) {
                    unitPart = this.qty.toFixed(0);
                } else {
                    const formatted = formatFloat(this.qty, { digits: [69, ProductUnit.digits] });
                    const parts = formatted.split(decimalPoint);
                    unitPart = parts[0];
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
            decimalPoint: decimalPoint,
            decimalPart: decimalPart,
        };
    }

    get company() {
        return this.config.company_id;
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
            lotLine.delete();
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
            const maxQtyToRefund = refundDetails.line.qty - refundDetails.line.refundedQty;
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

        const rounder =
            this.product_id.uom_id ||
            this.models["decimal.precision"].find((dp) => dp.name === "Product Unit");

        this.qty = rounder.round(quant);

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
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        const price = ProductPrice.round(this.price_unit || 0);
        const product = orderline.getProduct();
        let order_line_price = product.getPrice(
            orderline.order_id.pricelist_id,
            this.getQuantity(),
            0,
            false,
            product
        );
        order_line_price = this.currency.round(order_line_price);

        const isSameCustomerNote =
            (Boolean(orderline.getCustomerNote()) === false &&
                Boolean(this.getCustomerNote()) === false) ||
            orderline.getCustomerNote() === this.getCustomerNote();

        // only orderlines of the same product can be merged
        return (
            orderline.getNote() === this.getNote() &&
            this.getProduct().id === orderline.getProduct().id &&
            this.isPosGroupable() &&
            // don't merge discounted orderlines
            this.getDiscount() === 0 &&
            this.currency.isZero(price - order_line_price - orderline.getPriceExtra()) &&
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

    prepareBaseLineForTaxesComputationExtraValues(customValues = {}) {
        const order = this.order_id;
        const currency = order.config.currency_id;
        const extraValues = { currency_id: currency };
        const product = this.getProduct();
        const priceUnit = this.getUnitPrice();
        const discount = this.getDiscount();

        const values = {
            ...extraValues,
            quantity: this.qty,
            price_unit: priceUnit,
            discount: discount,
            tax_ids: this.tax_ids,
            product_id: product,
            rate: 1.0,
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

    setUnitPrice(price) {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        const parsed_price = !isNaN(price)
            ? price
            : isNaN(parseFloat(price))
            ? 0
            : parseFloat("" + price);
        this.price_unit = ProductPrice.round(parsed_price || 0);
    }

    getUnitPrice() {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        return ProductPrice.round(this.price_unit || 0);
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
        return this.currency.round(
            this.getUnitPrice() * this.getQuantity() * (1 - this.getDiscount() / 100)
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
        const company = this.company;
        const product = this.getProduct();
        const baseLine = accountTaxHelpers.prepare_base_line_for_taxes_computation(
            this,
            this.prepareBaseLineForTaxesComputationExtraValues({
                price_unit: this.getlstPrice(),
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

    getAllPrices(qty = this.getQuantity()) {
        const company = this.company;
        const product = this.getProduct();
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

    computePriceWithTaxBeforeDiscount() {
        return this.combo_line_ids.length > 0
            ? // total of all combo lines if it is combo parent
              formatCurrency(
                  this.combo_line_ids.reduce(
                      (total, cl) => total + cl.allPrices.priceWithTaxBeforeDiscount,
                      0
                  ),
                  this.currency
              )
            : formatCurrency(this.allPrices.priceWithTaxBeforeDiscount, this.currency);
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
    }

    getCustomerNote() {
        return this.customer_note || "";
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
                getTaxesAfterFiscalPosition(
                    this.product_id.taxes_id,
                    this.order_id.fiscal_position_id,
                    this.models
                )
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
        this.uiState.savedQuantity = this.qty;
    }
    getPriceExtra() {
        return this.price_extra;
    }
    getNote() {
        return this.note || "[]";
    }
    setNote(note) {
        this.note = note || "[]";
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
    get orderDisplayProductName() {
        return {
            name: this.product_id?.name,
            attributeString: constructAttributeString(this),
        };
    }
    isSelected() {
        return this.order_id?.uiState?.selected_orderline_uuid === this.uuid;
    }
    get canBeRemoved() {
        return this.product_id.uom_id.isZero(this.qty);
    }
    get refundedQty() {
        return (
            this.refund_orderline_ids?.reduce(
                (acc, line) => (line.order_id.state !== "cancel" ? acc - line.qty : acc),
                0
            ) || 0
        );
    }
}

registry.category("pos_available_models").add(PosOrderline.pythonModel, PosOrderline);
