import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { Dialog } from "@web/core/dialog/dialog";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

// This is functionally identical to the base ScaleScreen component.
// Having a separate copy allows us to keep a certified version that will only change
// if absolutely necessary, whilst the base component is free to change.

export class CertifiedScaleScreen extends Component {
    static template = "l10n_eu_iot_scale_cert.CertifiedScaleScreen";
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
        this.props.getPayload(this.scale.confirmWeight());
        this.props.close();
    }

    onError(message) {
        this.props.getPayload(null);
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
