import { Component, onMounted, signal } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { renderToElement } from "@web/core/utils/render";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class TestPopup extends Component {
    static template = "point_of_sale.TestPopup";
    static components = { Dialog };

    ref = signal.ref();

    setup() {
        this.pos = usePos();

        onMounted(() => this.fetchReceiptTemplate());
    }

    async fetchReceiptTemplate() {
        const data = await this.pos.data.call("pos.order", "get_example_order_data");
        const el = renderToElement("point_of_sale.pos_order_receipt", data);
        console.log(data);
        this.ref().appendChild(el);
    }
}
