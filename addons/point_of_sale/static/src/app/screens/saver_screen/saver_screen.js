import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useTime } from "@point_of_sale/app/hooks/time_hook";

export class SaverScreen extends Component {
    static template = "point_of_sale.SaverScreen";
    static storeOnOrder = false;
    static updatePreviousScreen = false;
    static props = [];

    setup() {
        this.time = useTime();
    }
}

registry.category("pos_pages").add("SaverScreen", {
    name: "SaverScreen",
    component: SaverScreen,
    route: `/pos/ui/${odoo.pos_config_id}/saver`,
    params: {},
});
