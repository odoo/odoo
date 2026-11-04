import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useTime } from "@point_of_sale/app/utils/time_hook";
import { useService } from "@web/core/utils/hooks";

export class SaverScreen extends Component {
    static template = "point_of_sale.SaverScreen";
    static storeOnOrder = false;
    static updatePreviousScreen = false;
    static props = [];

    setup() {
        this.time = useTime();
        this.overlayService = useService("overlay");
        this.closeAllOverlays();
    }

    closeAllOverlays() {
        Object.values(this.overlayService.overlays).forEach((overlay) => overlay.remove());
    }
}

registry.category("pos_screens").add("SaverScreen", SaverScreen);
