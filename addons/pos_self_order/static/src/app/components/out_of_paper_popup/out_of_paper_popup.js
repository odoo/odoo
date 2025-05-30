import { Component, onWillUnmount } from "@odoo/owl";

export class OutOfPaperPopup extends Component {
    static template = "pos_self_order.OutOfPaperPopup";
    static props = {
        trackingNumber: String,
        close: Function,
    };

    setup() {
        const timeout = setTimeout(() => {
            this.props.close();
        }, 10000);

        onWillUnmount(() => {
            clearTimeout(timeout);
        });
    }
}
