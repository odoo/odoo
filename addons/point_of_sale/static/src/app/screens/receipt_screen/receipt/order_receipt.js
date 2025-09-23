import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";
import { generateQRCodeDataUrl } from "@point_of_sale/utils";

export class OrderReceipt extends Component {
    static template = "point_of_sale.OrderReceipt";
    static components = {
        Orderline,
        OrderDisplay,
        ReceiptHeader,
    };
    static props = {
        order: Object,
        basic_receipt: { type: Boolean, optional: true },
    };
    static defaultProps = {
        basic_receipt: false,
    };

    get header() {
        return {
            company: this.order.company,
            cashier: _t("Served by %s", this.order?.getCashierName()),
            header: this.order.config.receipt_header,
        };
    }

    get order() {
        return this.props.order;
    }

    get qrCode() {
        const baseUrl = this.order.config._base_url;
        const url = `${baseUrl}/pos/ticket?order_uuid=${this.order.uuid}`;
        return generateQRCodeDataUrl(url);
    }

    get paymentLines() {
        return this.order.payment_ids.filter((p) => !p.is_change);
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
}
