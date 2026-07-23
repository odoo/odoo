import { Component, onWillUnmount, t, useProps } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class PrintingFailurePopup extends Component {
    static template = "pos_self_order.PrintingFailurePopup";
    props = useProps({
        trackingNumber: t.string(),
        title: t.string().optional(_t("Printing failed")),
        message: t.string(),
        close: t.function(),
    });

    setup() {
        const timeout = setTimeout(() => {
            this.props.close();
        }, 20000);

        onWillUnmount(() => {
            clearTimeout(timeout);
        });
    }
}
