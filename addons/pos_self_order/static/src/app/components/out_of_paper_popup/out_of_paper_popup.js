import { Component } from "@odoo/owl";

export class OutOfPaperPopup extends Component {
    static template = "pos_self_order.OutOfPaperPopup";
    static props = {
        title: String,
        close: Function,
    };

    setup() {
        setTimeout(() => {
            this.props.close();
        }, 10000);
    }
}
