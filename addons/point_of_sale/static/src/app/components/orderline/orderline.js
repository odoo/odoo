import { Component, useRef } from "@odoo/owl";
import { useTimedPress } from "@point_of_sale/app/utils/use_timed_press";
import { formatCurrency } from "@web/core/currency";
import { TagsList } from "@web/core/tags_list/tags_list";

export class Orderline extends Component {
    static components = { TagsList };
    static template = "point_of_sale.Orderline";
    static props = {
        line: Object,
        class: { type: Object, optional: true },
        slots: { type: Object, optional: true },
        showTaxGroupLabels: { type: Boolean, optional: true },
        showTaxGroup: { type: Boolean, optional: true },
        mode: { type: String, optional: true }, // display, receipt
        basic_receipt: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
        onLongPress: { type: Function, optional: true },
    };
    static defaultProps = {
        showImage: false,
        showTaxGroupLabels: false,
        showTaxGroup: false,
        mode: "display",
        basic_receipt: false,
        onClick: () => {},
        onLongPress: () => {},
    };

    setup() {
        this.root = useRef("root");
        if (this.props.mode === "display") {
            useTimedPress(this.root, [
                {
                    type: "release",
                    maxDelay: 500,
                    callback: (event, duration) => {
                        this.props.onClick(event, duration);
                    },
                },
                {
                    type: "hold",
                    delay: 500,
                    callback: (event, duration) => {
                        this.props.onLongPress(event, duration);
                    },
                },
            ]);
        }
    }

    get line() {
        return this.props.line;
    }

    get lineContainerClasses() {
        return {
            selected: this.line.isSelected() && this.props.mode === "display",
            ...this.line.getDisplayClasses(),
            ...(this.props.class || []),
            "border-start": this.props.mode != "receipt" && this.line.combo_parent_id,
            "orderline-combo fst-italic ms-4": this.line.combo_parent_id,
            "position-relative d-flex align-items-center lh-sm cursor-pointer": true, // Keep all classes here
        };
    }

    get lineClasses() {
        const line = this.line;
        const props = this.props;
        if (line.combo_parent_id) {
            return props.mode === "receipt" ? "px-2" : "p-2";
        } else {
            if (props.mode === "receipt") {
                return line.combo_line_ids.length > 0 ? "" : "py-1";
            } else {
                return "p-2";
            }
        }
    }

    get infoListClasses() {
        const line = this.line;
        const props = this.props;
        if (props.mode === "receipt") {
            return "";
        }
        if (line.customer_note || line.note || line.discount || line.packLotLines?.length) {
            return "gap-2 mt-1";
        }
        return "";
    }

    /**
     * To avoid to much logic in the template, we compute all values here
     * and use them in the template.
     */
    get lineScreenValues() {
        const line = this.line;

        // Prevent rendering if the line is not yet linked to an order
        // this can happen during related models connections
        if (!line.order_id) {
            return {};
        }

        const imageUrl = line.product_id?.getImageUrl();
        const basic = this.props.basic_receipt;
        const unitPart = line.getQuantityStr().unitPart;
        const decimalPart = line.getQuantityStr().decimalPart;
        const decimalPoint = line.getQuantityStr().decimalPoint;
        const discount = line.getDiscountStr();
        const mode = this.props.mode;
        const attributeStr = line.orderDisplayProductName.attributeString;
        const taxGroup = [
            ...new Set(
                this.line.product_id.taxes_id
                    ?.map((tax) => tax.tax_group_id.pos_receipt_label)
                    .filter((label) => label)
            ),
        ].join(" ");
        const showPrice =
            !basic &&
            line.getQuantityStr() != 1 &&
            (mode === "receipt" || (line.price_type !== "original" && !line.combo_parent_id));
        const priceUnit = `${line.currencyDisplayPriceUnit} / ${
            line.product_id?.uom_id?.name || ""
        }`;
        return {
            name: mode === "receipt" ? line.full_product_name : line.orderDisplayProductName.name,
            attributeString: mode === "display" && attributeStr && `- ${attributeStr}`,
            internalNote: mode === "display" && line.note && JSON.parse(this.line.note || "[]"),
            isReceipt: mode === "receipt",
            isDisplay: mode === "display",
            discount: !basic && discount && discount !== "0" && !line.combo_parent_id && discount,
            noDiscountPrice: formatCurrency(line.displayPriceNoDiscount, line.currency.id),
            displayPriceUnit: showPrice && line.price !== 0 && priceUnit,
            unitPart: unitPart,
            decimalPart: decimalPart && `${decimalPoint}${decimalPart}`,
            productImage: this.props.showImage && imageUrl,
            taxGroup: this.props.showTaxGroup && taxGroup,
            price: !basic && !line.combo_parent_id && this.line.currencyDisplayPrice,
            lotLines: line.product_id.tracking !== "none" && (line.packLotLines || []),
        };
    }
}
