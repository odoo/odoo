import { services } from "@web/core/services";
import { Plugin, usePlugin } from "@odoo/owl";
import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { Alert } from "@point_of_sale/app/components/pos_alert/pos_alert";

export class PosAlertPlugin extends Plugin {
    overlay = usePlugin(OverlayPlugin);

    setup() {
        this._dismiss = null;
    }

    remove() {
        if (this._dismiss) {
            this._dismiss();
            this._dismiss = null;
        }
    }

    add(message, options = {}, overlayOptions = {}) {
        this.remove();
        this._dismiss = this.overlay.add(
            Alert,
            {
                message,
                ...options,
                onClose: () => {
                    this.remove();
                    options.onClose?.();
                },
            },
            overlayOptions
        );
    }
}

services.add(PosAlertPlugin);
