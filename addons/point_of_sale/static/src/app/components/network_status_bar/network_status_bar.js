import { Component, useOnChange, signal } from "@odoo/owl";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";

export class NetworkStatusBar extends Component {
    static template = "point_of_sale.NetworkStatusBar";

    stateTimeGuard = signal("");
    setup() {
        this.pos = usePos();
        this.timeout = null;

        useOnChange(
            () => [this.pos.data.network.loading, this.pos.data.network.offline],
            () => {
                this.stateTimeGuard.set(this.state);
                if (this.timeout) {
                    clearTimeout(this.timeout);
                }

                this.timeout = setTimeout(() => this.stateTimeGuard.set(""), 1100);
                return () => clearTimeout(this.timeout);
            },
            { initialRun: false }
        );
    }

    get state() {
        if (this.pos.data.network.offline || this.stateTimeGuard() === "offline") {
            return "offline";
        }
        if (this.pos.data.network.loading || this.stateTimeGuard() === "syncing") {
            return "syncing";
        }
        return "online";
    }
}
