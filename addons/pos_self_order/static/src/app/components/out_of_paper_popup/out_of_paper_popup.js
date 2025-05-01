import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class OutOfPaperPopup extends Component {
    static template = "pos_self_order.OutOfPaperPopup";
    static props = {
        title: { type: String, optional: true },
        message: String,
        close: Function,
    };

    static defaultProps = {
        title: _t("Printing failed"),
    };

    setup() {
        setTimeout(() => {
            this.props.close();
        }, 20000);
    }
}
