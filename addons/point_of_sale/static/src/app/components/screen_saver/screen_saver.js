import { usePos } from "@point_of_sale/app/store/pos_hook";
import { Component } from "@odoo/owl";
import { useTime } from "@point_of_sale/app/utils/time_hook";
import { useIdleTimer } from "@point_of_sale/app/utils/use_idle_timer";

export class ScreenSaver extends Component {
    static template = "point_of_sale.ScreenSaver";
    static components = {};
    static props = [];

    setup() {
        this.pos = usePos();
        this.time = useTime();
        this.timer = useIdleTimer(4000);
    }
}
