import { Component, markup } from "@odoo/owl";
import { formatCurrency } from "@web/core/currency";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { TagsList } from "@web/core/tags_list/tags_list";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { qrCodeSrc, imageDataUri } from "@point_of_sale/utils";

const { DateTime } = luxon;

export class OrderReceipt extends Component {
    static template = "point_of_sale.OrderReceipt";
    static components = {
        ReceiptHeader,
        TagsList,
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
        const baseUrl = this.order.config._base_url;
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

    get orderQuantity() {
        return this.orderLines.reduce((acc, line) => acc + line.qty, 0);
    }

    get internalNotes() {
        return JSON.parse(this.order.internal_note || "[]");
    }

    get bgImageUrl() {
        const { receipt_bg_layout, receipt_bg_image, receipt_logo } = this.order.config;

        if (receipt_bg_layout == "blank") {
            return false;
        }
        if (receipt_bg_layout == "config_logo") {
            return receipt_logo ? imageDataUri(receipt_logo) : false;
        }
        return receipt_bg_image ? imageDataUri(receipt_bg_image) : false;
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.order.currency.id);
    }

    doesAnyOrderlineHaveTaxLabel() {
        return this.order.lines?.some((line) => line.taxGroupLabels);
    }

    getPortalURL() {
        return `${this.order.config._base_url}/pos/ticket`;
    }

    get vatText() {
        if (this.order.company.country_id?.vat_label) {
            return _t("%(vatLabel)s: %(vatId)s", {
                vatLabel: this.order.company.country_id.vat_label,
                vatId: this.order.company.vat,
            });
        }
        return _t("Tax ID: %(vatId)s", { vatId: this.order.company.vat });
    }

    get receiptClasses() {
        return {
            table: `table border-dark mb-0 text-start ${
                this.layout === "boxes" ? "table-bordered" : "table-borderless"
            }`,
            thr: {
                "border-top border-bottom border-dark": this.layout === "lined",
                "d-none": this.isDefaultLayout,
            },
        };
    }

    get isDefaultLayout() {
        return this.layout == "default";
    }

    // meant to override these when ever needed to add/hide any columns
    get layoutColumnKeys() {
        return {
            lined: ["name", "qty", "priceUnit", "price"],
            boxes: ["index", "name", "price"],
            default: ["qty", "name", "price"],
        };
    }
    get headerColumnsData() {
        return {
            index: { class: "index", value: _t("No.") },
            name: { class: "name", value: _t("Item") },
            qty: { class: "qty", value: _t("Qty") },
            priceUnit: { class: "price-per-unit", value: _t("Price") },
            price: { class: "product-price price", value: _t("Total") },
            priceTaxLabel: { class: "product-tax-label", value: _t("Tax Label") },
        };
    }

    get layoutKey() {
        const columnLeys = this.props.basic_receipt
            ? this.layoutColumnKeys[this.layout].filter((key) => !key.includes("price"))
            : this.layoutColumnKeys[this.layout];

        if (this.doesAnyOrderlineHaveTaxLabel()) {
            columnLeys.push("priceTaxLabel");
        }
        return columnLeys;
    }

    get headerInfo() {
        return this.layoutKey.map((key) => this.headerColumnsData[key]);
    }

    lineData(line, lineIndex) {
        return {
            index: { class: "index", value: lineIndex + 1 },
            name: {
                class: "product-name",
                value: line.orderDisplayProductName.name,
                other: this._getAdditionalLineInfo(line),
            },
            qty: { class: "qty", value: line.qty },
            priceUnit: {
                class: "price-per-unit",
                value: this.formatCurrency(line.unitDisplayPrice),
            },
            price: { class: "product-price price", value: line.getPriceString() },
            priceTaxLabel: { class: "product-tax-label text-end", value: line.taxGroupLabels },
        };
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
        if (
            !this.props.basic_receipt &&
            this.isDefaultLayout &&
            line.price !== 0 &&
            line.qty != 1 &&
            line.price_type !== "original"
        ) {
            info.push({
                class: "price-per-unit",
                value: `${this.formatCurrency(line.unitDisplayPrice)} / ${
                    line.product_id.uom_id?.name || ""
                }`,
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
                class: "discount",
                value: _t(
                    "%s with a %s% discount",
                    this.formatCurrency(line.allPrices.priceWithTaxBeforeDiscount),
                    discount
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
            info.push({ class: "lot-number", value: lotLine });
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
        const _getPreviewOrderLine = (product, index) => {
            const qty = (product.id % 8) + 1;
            return {
                orderDisplayProductName: { name: product.name },
                qty: qty,
                unitDisplayPrice: product.list_price,
                getPriceString: () => this.formatCurrency(qty * product.list_price),
                getDiscountStr: () => false,
                product_id: { uom_id: { name: product.uom_id[1] } },
            };
        };

        const orderLines = this.props.product_data.map(_getPreviewOrderLine);
        const orderTotal = orderLines.reduce(
            (acc, line) => acc + line.unitDisplayPrice * line.qty,
            0
        );
        const taxTotals = {
            has_tax_groups: true,
            same_tax_base: true,
            order_total: orderTotal,
            order_sign: 1,
            subtotals: [
                {
                    name: _t("Untaxed Amount"),
                    base_amount_currency: orderTotal * 0.95,
                    tax_groups: [
                        {
                            id: 1,
                            group_label: false,
                            group_name: _t("Tax 5%"),
                            base_amount_currency: orderTotal * 0.95,
                            tax_amount_currency: orderTotal * 0.05,
                        },
                    ],
                },
            ],
        };
        const paymentLines = [
            {
                id: 1,
                is_change: false,
                getAmount: () => orderTotal,
                payment_method_id: {
                    name: _t("Cash"),
                },
            },
        ];
        return {
            getTotalDiscount: () => false,
            config: this.props.config_data,
            company: this.props.company_data,
            currency: { id: this.props.config_data.currency_id },
            lines: orderLines,
            taxTotals: taxTotals,
            payment_ids: paymentLines,
            pos_reference: "2504-003-0001",
            formatDateOrTime: () => DateTime.now().toLocaleString(DateTime.DATETIME_SHORT),
            getCashierName: () => _t("Mitchell Admin"),
            session: {},
            tracking_number: "021",
            date_order: DateTime.now(),
        };
    }
}

registry.category("lazy_components").add("OrderReceipt", OrderReceipt);
