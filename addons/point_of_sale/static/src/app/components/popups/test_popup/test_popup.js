import { useLayoutEffect } from "@web/owl2/utils";
import { Component, signal } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { renderToElement } from "@web/core/utils/render";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class TestPopup extends Component {
    static template = "point_of_sale.TestPopup";
    static components = { Dialog };

    ref = signal(null);

    setup() {
        this.pos = usePos();

        useLayoutEffect(
            () => {
                if (this.ref()) {
                    this.fetchReceiptTemplate();
                }
            },
            () => [this.ref()]
        );
    }

    async fetchReceiptTemplate() {
        const data = await this.pos.data.call("pos.order", "get_example_order_data");
        const el = renderToElement("point_of_sale.pos_order_receipt", data);
        console.log(data);
        this.ref().appendChild(el);
    }
}
