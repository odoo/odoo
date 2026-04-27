import { DebugWidget } from "@point_of_sale/app/debug/debug_widget";
import { patch } from "@web/core/utils/patch";

patch(DebugWidget.prototype, {
    /**
     * @override
     */
    refreshDisplay() {
        if (this.hardwareProxy.display) {
            this.hardwareProxy.display.action({ action: "display_refresh" });
        }
    },
});
