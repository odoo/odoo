import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class ScaleScreen extends Component {
    static template = "point_of_sale.ScaleScreen";
    static components = { Dialog };
    static props = {
        getPayload: Function,
        close: Function,
    };

    setup() {
        this.scale = useState(useService("pos_scale"));
        this.dialog = useService("dialog");
        onMounted(() => this.scale.start(this.onError.bind(this)));
        onWillUnmount(() => this.scale.reset());
    }

    confirm() {
        this.props.getPayload(this.scale.netWeight);
        this.props.close();
    }

    onError(message) {
        this.dialog.add(
            AlertDialog,
            {
                title: _t("Scale error"),
                body: message,
            },
            { onClose: this.props.close }
        );
    }
}
