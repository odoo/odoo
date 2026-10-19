import { OverlayPlugin } from "@web/core/overlay/overlay_plugin";
import { registry } from "@web/core/registry";
import { Component, usePlugin } from "@odoo/owl";
import { useTime } from "@point_of_sale/app/hooks/time_hook";
import { useService } from "@web/core/utils/hooks";

export class SaverScreen extends Component {
    static template = "point_of_sale.SaverScreen";
    static storeOnOrder = false;
    static updatePreviousScreen = false;

    setup() {
        this.time = useTime();
        this.uiService = useService("ui");
        this.overlayService = usePlugin(OverlayPlugin);
        this.closeAllOverlays();
    }

    closeAllOverlays() {
        this.overlayService.overlays.items().forEach((overlay) => overlay.remove());
    }
}

registry.category("pos_pages").add("SaverScreen", {
    name: "SaverScreen",
    component: SaverScreen,
    route: `/pos/ui/${odoo.pos_config_id}/saver`,
    params: {},
});
