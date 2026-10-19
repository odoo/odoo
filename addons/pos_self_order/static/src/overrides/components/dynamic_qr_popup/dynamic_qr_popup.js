import { Dialog } from "@web/core/dialog/dialog";
import { Component, props, t } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class DynamicQrPopup extends Component {
    static template = "pos_self_order.DynamicQrPopup";
    static components = { Dialog };
    props = props({
        qrCode: t.string(),
        url: t.string(),
        order: t.object(),
        close: t.function().optional(),
    });

    setup() {
        this.pos = usePos();
    }

    async printQrCode() {
        await this.pos.ticketPrinter.printDynamicQrReceipt({
            order: this.props.order,
            qrCode: this.props.qrCode,
        });
    }
}
