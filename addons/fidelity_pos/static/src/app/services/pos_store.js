import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";
import { debounce } from "@web/core/utils/timing";

export const CONSOLE_COLOR = "#ff6565ff";

patch(PosStore.prototype, {
    async setup() {
        await super.setup(...arguments);
        this.debounceCheckFidelity = debounce(this.checkFidelityPrograms.bind(this), 300);

        for (const event of ["create", "update", "delete"]) {
            for (const model of ["pos.order", "pos.order.line"]) {
                this.models[model].addEventListener(event, this.debounceCheckFidelity.bind(this));
            }
        }
    },
    checkFidelityPrograms() {
        const order = this.getOrder();
        const programs = this.models["fidelity.program"].getAll();
        for (const program of programs) {
            program.redeemablePoints(order);
        }
        logPosMessage(
            "Fidelity",
            "checkFidelityPrograms",
            "Should check fidelity programs now.",
            CONSOLE_COLOR
        );
    },
});
