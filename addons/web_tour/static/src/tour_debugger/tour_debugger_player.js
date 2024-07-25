import { EventBus } from "@odoo/owl";

class TourDebuggerPlayer {
    tour;
    status = "PAUSED";
    constructor() {
        this.prefix = "TOUR_DEBUGGER_";
        this.bus = new EventBus();
    }

    waitFor = (status) => {
        return new Promise((resolve) => {
            if (this.status === status) {
                resolve();
            }
            this.bus.addEventListener(this.prefix + status, (event) => {
                this.setStatus(status);
                resolve(event);
            });
        });
    };

    setStatus = (status) => {
        this.status = status;
        this.render();
    };

    render = () => {
        this.trigger("RENDER");
    };

    trigger = (status) => {
        this.bus.trigger(this.prefix + status);
    };
}

const tourDebuggerPlayer = new TourDebuggerPlayer();
export { tourDebuggerPlayer };
