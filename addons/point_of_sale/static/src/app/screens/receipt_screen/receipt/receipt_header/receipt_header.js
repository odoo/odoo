import { Component, markup } from "@odoo/owl";
import { imageDataUri } from "@point_of_sale/utils";

export class ReceiptHeader extends Component {
    static template = "point_of_sale.ReceiptHeader";
    static props = {
        order: Object,
        previewMode: { type: Boolean, optional: true },
    };

    get order() {
        return this.props.order;
    }

    get partnerAddress() {
        return this.order.partner_id.pos_contact_address
            .split("\n")
            .filter((line) => line.trim() !== "")
            .join(", ");
    }

    get receiptLogoSrc() {
        if (this.order.config.receipt_logo) {
            return imageDataUri(this.order.config.receipt_logo);
        }
        // If in preview mode, show a placeholder image if no logo is selected
        return this.props.previewMode ? "/web/static/img/placeholder.png" : false;
    }

    get headerMarkup() {
        return markup(this.order.config.receipt_header);
    }
}
