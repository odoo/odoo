import { usePlugin } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { CustomerDisplayTerminalPlugin } from "@point_of_sale/app/plugins/customer_display_terminal_plugin";
import { PosAccessRightPlugin } from "@point_of_sale/app/plugins/access_right_plugin";

patch(CustomerDisplayTerminalPlugin.prototype, {
    setup() {
        super.setup(...arguments);
        this.accessRight = usePlugin(PosAccessRightPlugin);
    },
    _buildDisplayPayload(order) {
        const payload = super._buildDisplayPayload(order);
        payload.loyaltyPrograms = [];
        if (!this.accessRight.canApplyRewards) {
            return payload;
        }

        const round = (value) => parseFloat(value.toFixed(2));
        for (const program of order.models["loyalty.program"].filter(
            (program) => program.program_type === "loyalty"
        )) {
            const won = program.getEarnedPoints(order);
            const spent = program.getSpentPoints(order);
            const balance = program.getAvailablePoints(order);
            const total = program.getNewBalance(order);
            if (!won && !spent && !balance) {
                continue;
            }
            payload.loyaltyPrograms.push({
                id: program.id,
                name: program.name,
                won: round(won),
                spent: round(spent),
                balance: round(balance),
                total: round(total),
            });
        }
        return payload;
    },
});
