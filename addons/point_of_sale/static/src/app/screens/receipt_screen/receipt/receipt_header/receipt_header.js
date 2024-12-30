import { Component } from "@odoo/owl";

export class ReceiptHeader extends Component {
    static template = "point_of_sale.ReceiptHeader";
    static props = {
        order: Object,
    };

    get order() {
        return this.props.order;
    }

    get partnerAddress() {
        return this.order.partner_id.pos_contact_address.split("\n");
    }
}
