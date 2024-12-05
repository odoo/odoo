import { registry } from "@web/core/registry";
import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { useTime } from "@point_of_sale/app/utils/time_hook";

export class ScreenSaver extends Component {
    static template = "point_of_sale.ScreenSaver";
    static storeOnOrder = false;
    setup() {
        this.pos = usePos();
        this.time = useTime();
    }
}

registry.category("pos_screens").add("ScreenSaver", ScreenSaver);
