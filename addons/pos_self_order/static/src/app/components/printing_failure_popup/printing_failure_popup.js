import { Component, onWillUnmount, props, types } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class PrintingFailurePopup extends Component {
    static template = "pos_self_order.PrintingFailurePopup";
    props = props(
        {
            trackingNumber: types.string(),
            "title?": types.string(),
            message: types.string(),
            close: types.function(),
        },
        {
            title: _t("Printing failed"),
        }
    );

    setup() {
        const timeout = setTimeout(() => {
            this.props.close();
        }, 20000);

        onWillUnmount(() => {
            clearTimeout(timeout);
        });
    }
}
