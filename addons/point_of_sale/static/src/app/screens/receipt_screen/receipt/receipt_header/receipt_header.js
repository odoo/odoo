import { Component } from "@odoo/owl";

export class ReceiptHeader extends Component {
    static template = "point_of_sale.ReceiptHeader";
    static props = {
        order: Object,
    };

    get order() {
        return this.props.order;
    }

    get logoUrl() {
        return this.order.config.receiptLogoUrl;
    }

    get partnerAddress() {
        // TODO : REMOVE ME IN MASTER
        return this.order.partner_id.pos_contact_address
            .split("\n")
            .filter((line) => line.trim() !== "")
            .join(", ");
    }
}
