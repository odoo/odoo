import { Component, signal } from "@odoo/owl";
import { useSelfOrder } from "@pos_self_order/app/services/self_order_service";
import { useService } from "@web/core/utils/hooks";
import { useScrollShadow } from "../../utils/scroll_shadow_hook";
import { SIZES } from "@web/core/ui/ui_utils";

export class EatingLocationPage extends Component {
    static template = "pos_self_order.EatingLocationPage";

    scrollContainerRef = signal.ref();

    setup() {
        this.selfOrder = useSelfOrder();
        this.router = useService("router");
        this.scrollShadow = useScrollShadow(this.scrollContainerRef);
        this.ui = useService("ui");
        this.SIZES = SIZES;
    }

    onClickBack() {
        this.router.navigate(history.state?.redirectPage || "default");
    }

    selectPreset(preset) {
        const order = this.selfOrder.currentOrder;
        // Reset tip when switching to a different preset, as pricelist or fiscal
        // position may differ, which would change the order total and invalidate
        // the previously computed tip amount or percentage.
        if (order.preset_id !== preset) {
            this.selfOrder.resetTip();
        }
        order.setPreset(preset);
        this.router.navigate(history.state?.redirectPage || "product_list");
    }

    /**
     * Presets offered for eating-location selection.
     * Table-service presets are hidden unless a table is known (kiosk, scanned QR, or dynamic_qr order).
     * In dynamic_qr mode, only table-service presets are offered, since the order is already tied to that table.
     */
    get presets() {
        return this.selfOrder.availablePresets;
    }
}
