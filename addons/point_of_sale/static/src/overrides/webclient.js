import { WebClient } from "@web/webclient/webclient";
import { onWillStart } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(WebClient.prototype, {
    setup() {
        super.setup();
        onWillStart(this.registerServiceWorkerPOS);
    },
    registerServiceWorkerPOS() {
        if (navigator.serviceWorker) {
            navigator.serviceWorker
                .register("/pos/service-worker.js", { scope: "/pos" })
                .catch((error) => {
                    console.error("Custom Service worker registration failed, error:", error);
                });
        }
    },
});
