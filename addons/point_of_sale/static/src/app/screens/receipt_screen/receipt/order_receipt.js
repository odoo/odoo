import { Component } from "@odoo/owl";
import { Orderline } from "@point_of_sale/app/components/orderline/orderline";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { qrCodeSrc } from "@point_of_sale/utils";
import { _t } from "@web/core/l10n/translation";
import { formatCurrency } from "@web/core/currency";

export class OrderReceipt extends Component {
    static template = "point_of_sale.OrderReceipt";
    static components = {
        Orderline,
        OrderDisplay,
        ReceiptHeader,
    };
    static props = {
        order: Object,
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
        const baseUrl = this.order.session._base_url;
        return (
            this.order.company.point_of_sale_use_ticket_qr_code &&
            this.order.finalized &&
            qrCodeSrc(`${baseUrl}/pos/ticket/`)
        );
    }

    get paymentLines() {
        return this.order.payment_ids.filter((p) => !p.is_change);
    }

    formatCurrency(amount) {
        return formatCurrency(amount, this.order.currency.id);
    }

    doesAnyOrderlineHaveTaxLabel() {
        return this.order.lines.some((line) => line.taxGroupLabels);
    }
}
