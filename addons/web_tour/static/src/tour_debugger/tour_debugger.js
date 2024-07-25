import { Component } from "@odoo/owl";
import { tourDebuggerPlayer } from "./tour_debugger_player";
import { useBus } from "@web/core/utils/hooks";

export class TourDebugger extends Component {
    static template = "web_tour.TourDebugger";
    static props = {
        tour: { type: Object },
    };
    setup() {
        this.player = tourDebuggerPlayer;
        useBus(this.player.bus, "TOUR_DEBUGGER_RENDER", () => {
            this.render();
        });
    }
}
