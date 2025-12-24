import { registry } from "@web/core/registry";
import { constructFullProductName, constructAttributeString } from "@point_of_sale/utils";
import { parseFloat } from "@web/views/fields/parsers";
import { formatFloat } from "@web/core/utils/numbers";
import { _t } from "@web/core/l10n/translation";
import { localization as l10n } from "@web/core/l10n/localization";
import { PosOrderlineAccounting } from "./accounting/pos_order_line_accounting";

export class PosOrderline extends PosOrderlineAccounting {
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
            oldQty: this.qty,
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

        const ProductUnit = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Unit"
        );
        if (unit) {
            if (ProductUnit.digits) {
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

    get selectedComboIds() {
        const allLines = this.getAllLinesInCombo();
        return allLines.reduce((acc, line) => {
            if (!line.combo_item_id) {
                return acc;
            }

            acc[line.combo_item_id.combo_id.id] = line.combo_item_id.id;
            return acc;
        }, {});
    }

    get selectedAttributes() {
        return this.attribute_value_ids.reduce((acc, attrValue) => {
            const customValue =
                this.custom_attribute_value_ids.find(
                    (c) => c.custom_product_template_attribute_value_id.id === attrValue.id
                )?.custom_value || "";

            if (attrValue.attribute_id.display_type === "multi") {
                if (!acc[attrValue.attribute_id.id]) {
                    acc[attrValue.attribute_id.id] = { selected: [], custom_value: customValue };
                }
                acc[attrValue.attribute_id.id].selected.push(attrValue);
            } else {
                acc[attrValue.attribute_id.id] = { selected: attrValue, custom_value: customValue };
            }
            return acc;
        }, {});
    }

    // To be overrided
    getDisplayClasses() {
        return {};
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
    }

    // sets the qty of the product. The qty will be rounded according to the
    // product's unity of measure properties. Quantities greater than zero will not get
    // rounded to zero
    setQuantity(quantity, keep_price) {
        this.uiState.oldQty = this.qty;
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

        const rounder = this.models["decimal.precision"].find((dp) => dp.name === "Product Unit");

        this.qty = rounder.round(quant);
        // just like in sale.order changing the qty will recompute the unit price
        this.setPrice(keep_price);
        for (const comboLine of this.combo_line_ids) {
            // If each combo contains 2 qty of a product, we wanna keep this ratio after setting the new quantity on the parent product.
            comboLine.setQuantity((comboLine.qty / this.uiState.oldQty || 1) * quantity, true);
        }
        return true;
    }

    setPrice(keep_price) {
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
    }

    canBeMergedWith(orderline) {
        const ProductPrice = this.models["decimal.precision"].find(
            (dp) => dp.name === "Product Price"
        );
        const price = ProductPrice.round(this.price_unit || 0);
        const product = orderline.getProduct();
        const order_line_price = product.getPrice(
            orderline.order_id.pricelist_id,
            this.getQuantity(),
            0,
            false,
            product
        );

        const isSameCustomerNote =
            (Boolean(orderline.getCustomerNote()) === false &&
                Boolean(this.getCustomerNote()) === false) ||
            orderline.getCustomerNote() === this.getCustomerNote();

        // only orderlines of the same product can be merged
        return (
            orderline.getNote() === this.getNote() &&
            this.getProduct().id === orderline.getProduct().id &&
            this.isPosGroupable() &&
            this.getDiscount() === orderline.getDiscount() &&
            this.price_type === orderline.price_type &&
            this.currency.isZero(
                this.currency.round(price) -
                    this.currency.round(order_line_price) -
                    orderline.getPriceExtra()
            ) &&
            this.full_product_name === orderline.full_product_name &&
            isSameCustomerNote &&
            !this.refunded_orderline_id &&
            !orderline.isPartOfCombo()
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

    get parentLine() {
        if (this.combo_parent_id) {
            return this.combo_parent_id.parentLine;
        }
        return this;
    }

    getDiscount() {
        return this.discount || 0;
    }

    get isValidForRefund() {
        return this.qty - this.refundedQty > 0 && !this.combo_parent_id;
    }

    // FIXME all below should be removed
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
