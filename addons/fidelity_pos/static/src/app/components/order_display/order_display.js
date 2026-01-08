import { OrderDisplay } from "@point_of_sale/app/components/order_display/order_display";
import { patch } from "@web/core/utils/patch";

// This methods is service-less, see PoS knowledges for more information
patch(OrderDisplay.prototype, {
    setup() {
        super.setup(...arguments);
    },
    get models() {
        return this.order.models;
    },
    get fidelityPointsByPrograms() {
        const pointsByPrograms = [];
        const order = this.order;
        const programs = this.models["fidelity.program"].getAll();
        for (const program of programs) {
            const points = program.redeemablePoints(order);
            if (points === 0) {
                continue;
            }

            pointsByPrograms.push({
                name: program.point_unit,
                points: points,
            });
        }
        return pointsByPrograms;
    },
});
