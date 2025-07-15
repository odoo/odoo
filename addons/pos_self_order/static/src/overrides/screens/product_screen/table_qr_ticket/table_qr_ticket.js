import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { ReceiptHeader } from "@point_of_sale/app/screens/receipt_screen/receipt/receipt_header/receipt_header";
import { qrCodeSrc } from "@point_of_sale/utils";
import { Component } from "@odoo/owl";

export class TableQrTicket extends Component {
    static template = "pos_self_order.TableQrTicket";
    static components = { ReceiptHeader };
    static props = {
        order: Object,
    };

    setup() {
        super.setup();
        this.pos = usePos();
    }

    get qrCode() {
        const baseRoute = `/pos-self/${this.pos.config.id}`;
        const baseUrl = this.pos.config._base_url;
        const fullUrl = `${baseUrl}${baseRoute}?access_token=${this.pos.config.access_token}&order_uuid=${this.props.order.uuid}`;
        console.log("QR Code URL:", fullUrl);
        return qrCodeSrc(fullUrl);
    }
}
