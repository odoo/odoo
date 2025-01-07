import { Component, markup } from "@odoo/owl";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { qrCodeSrc } from "@point_of_sale/utils";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";

const { DateTime } = luxon;

export class OrderReceipt extends Component {
    static template = "point_of_sale.OrderReceipt";
    static components = {
        ReceiptHeader,
    };
    static props = {
        order: Object,
        basic_receipt: { type: Boolean, optional: true },
    };
    static defaultProps = {
        basic_receipt: false,
    };

    get previewMode() {
        return this.props.previewMode || false;
    }

    get layout() {
        return this.order.config.receipt_layout;
    }

    get header() {
        return {
            company: this.order.company,
            cashier: _t("Served by %s", this.order?.getCashierName()),
            header: this.order.config.receipt_header,
        };
    }

    get order() {
        return this.previewMode ? this._getPreviewOrderData() : this.props.order;
    }

    get qrCode() {
        const baseUrl = this.order.session._base_url;
        return (
            !this.previewMode &&
            this.order.company.point_of_sale_use_ticket_qr_code &&
            this.order.finalized &&
            qrCodeSrc(`${baseUrl}/pos/ticket?order_uuid=${this.order.uuid}`)
        );
    }

    get footerMarkup() {
        return markup(this.order.config.receipt_footer);
    }

    get paymentLines() {
        return this.order.payment_ids.filter((p) => !p.is_change);
    }

    get orderLines() {
        return this.order.lines.filter((line) => !line.combo_parent_id);
    }

    get bgImageUrl() {
        const { receipt_bg_layout, receipt_bg_image } = this.order.config;
        const { id: companyId } = this.order.company;

        if (receipt_bg_layout === "blank") {
            return false;
        } else if (receipt_bg_layout === "demo_logo") {
            return `/web/image?model=res.company&id=${companyId}&field=logo`;
        }
        return receipt_bg_image ? `data:image/png;base64,${receipt_bg_image}` : false;
    }

    get orderQuantity() {
        return this.orderLines.reduce((acc, line) => acc + line.qty, 0);
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.order.currency.id);
    }

    doesAnyOrderlineHaveTaxLabel() {
        return this.order.lines.some((line) => line.taxGroupLabels);
    }

    getPortalURL() {
        return `${this.order.session._base_url}/pos/ticket`;
    }

    get receiptClasses() {
        return {
            table: `table border-dark mb-0 ${
                this.layout === "boxes" ? "table-boxes table-bordered" : "table-borderless"
            }`,
            thr: {
                "border-top border-bottom border-dark": this.layout === "lined",
                "d-none": this.layout === "light",
            },
        };
    }

    get showTaxTable() {
        return this.layout !== "light";
    }

    get showQty() {
        return this.layout !== "light";
    }

    // meant to override these when ever needed to add/hide any columns
    get layoutColumnKeys() {
        return {
            lined: ["index", "name", "qty", "priceUnit", "price"],
            boxes: ["index", "name", "price"],
            light: ["qty", "name", "price"],
        };
    }
    get headerColumnsData() {
        return {
            index: { class: "index", value: _t("No.") },
            qty: { class: "qty", value: _t("Qty") },
            name: { class: "name", value: _t("Item") },
            price: { class: "product-price price", value: _t("Total") },
            priceUnit: { class: "unit-price", value: _t("Price") },
        };
    }
    lineData(line, lineIndex) {
        return {
            qty: { class: "qty", value: line.qty },
            index: { class: "index", value: lineIndex + 1 },
            name: {
                class: "product-name",
                value: line.orderDisplayProductName.name,
                other: this._getAdditionalLineInfo(line),
            },
            price: { class: "product-price price", value: line.getPriceString() },
            priceUnit: {
                class: "unit-price",
                value: this.formatCurrency(line.unitDisplayPrice),
            },
        };
    }

    get layoutKey() {
        return this.props.basic_receipt
            ? this.layoutColumnKeys[this.layout].filter((key) => !key.includes("price"))
            : this.layoutColumnKeys[this.layout];
    }

    get headerInfo() {
        return this.layoutKey.map((key) => this.headerColumnsData[key]);
    }

    getLineInfo(line, lineIndex) {
        const lineData = this.lineData(line, lineIndex);
        return this.layoutKey.map((key) => lineData[key]);
    }

    // to add extra info below product name (i.e. customer note, lot number, etc.)
    _getAdditionalLineInfo(line) {
        const info = [];
        if (line.orderDisplayProductName.attributeString) {
            info.push({
                class: "attribute-line fst-italic ms-2",
                value: line.orderDisplayProductName.attributeString,
            });
        }
        if (this.layout === "boxes") {
            info.push({
                class: "qty",
                value:
                    line.qty +
                    (this.props.basic_receipt
                        ? " " + line.product_id.uom_id.name
                        : " x " + this.formatCurrency(line.unitDisplayPrice)),
            });
        }
        const discount = line.getDiscountStr();
        if (!this.props.basic_receipt && discount) {
            info.push({
                class: "price-per-unit",
                value: markup(
                    `${line.allPrices.priceWithTaxBeforeDiscount} with a <em>${discount}%</em> discount`
                ),
                iclass: "fa-tag",
            });
        }
        if (line.customer_note) {
            info.push({
                class: "customer-note",
                value: line.customer_note,
                iclass: "fa-sticky-note",
            });
        }
        line.packLotLines?.forEach((lotLine) => {
            info.push({ class: "pack-lot-line", value: lotLine });
        });
        if (line.combo_line_ids?.length) {
            let combo_info = _t("Combo Choice:");
            line.combo_line_ids.forEach(
                (cl) =>
                    (combo_info += `<div class="fw-bold fst-italic">- ${cl.getFullProductName()}</div>`)
            );
            info.push({
                class: "combo-options fw-bolder",
                value: markup(combo_info),
            });
        }
        return info;
    }

    _getPreviewOrderData() {
        const _getPreviewOrderLine = (name, qty, unitPrice) => ({
            orderDisplayProductName: { name: name },
            qty: qty,
            unitDisplayPrice: unitPrice,
            getPriceString: () => this.formatCurrency(qty * unitPrice),
            getDiscountStr: () => false,
            product_id: { uom_id: { name: "Units" } },
        });

        const taxTotals = {
            has_tax_groups: true,
            same_tax_base: true,
            order_total: 111.5,
            order_sign: 1,
            subtotals: [
                {
                    name: _t("Untaxed Amount"),
                    base_amount_currency: 106.2,
                    tax_groups: [
                        {
                            id: 1,
                            group_label: false,
                            group_name: "Tax 5%",
                            base_amount_currency: 106.2,
                            tax_amount_currency: 5.3,
                        },
                    ],
                },
            ],
        };
        const paymentLines = [
            {
                id: 1,
                is_change: false,
                getAmount: () => 111.5,
                payment_method_id: {
                    name: _t("Cash"),
                },
            },
        ];
        return {
            getTotalDiscount: () => false,
            totalQuantity: 9,
            config: this.props.config_data,
            company: this.props.company_data,
            currency: { id: this.props.config_data.currency_id },
            lines: [
                _getPreviewOrderLine("Pizza Margherita", 3, 11.5),
                _getPreviewOrderLine("Cheese Burger", 5, 13.0),
                _getPreviewOrderLine("Apple Pie", 1, 12),
            ],
            taxTotals: taxTotals,
            payment_ids: paymentLines,
            pos_reference: "2504-003-0001",
            formatDateOrTime: () => DateTime.now().toLocaleString(DateTime.DATETIME_SHORT),
            getCashierName: () => "Mitchell Admin",
            session: {},
        };
    }
}
