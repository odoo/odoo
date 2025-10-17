import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { qrCodeSrc } from "@point_of_sale/utils";
import { Component, markup } from "@odoo/owl";

export class OrderQrTicket extends Component {
    static template = "pos_self_order.OrderQrTicket";
    static props = { order: Object };

    setup() {
        super.setup();
        this.pos = usePos();
    }

    get ticketFooter() {
        return markup(this.pos.config.self_ordering_qr_ticket_footer || "");
    }

    get qrCode() {
        const { self_ordering_url } = this.pos.config;
        const { uuid } = this.props.order;
        const url = `${self_ordering_url}&order_uuid=${uuid}`;
        console.log("QR Code URL:", url); // TODO: remove debug log
        return qrCodeSrc(url);
    }
}
