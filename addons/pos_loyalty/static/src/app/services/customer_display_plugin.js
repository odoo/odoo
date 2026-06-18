import { patch } from "@web/core/utils/patch";
import { CustomerDisplayTerminalPlugin } from "@point_of_sale/app/plugins/customer_display_terminal_plugin";

patch(CustomerDisplayTerminalPlugin.prototype, {
    _buildDisplayPayload(order) {
        const round = (value) => parseFloat(value.toFixed(2));
        const loyaltyPrograms = [];
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
            loyaltyPrograms.push({
                id: program.id,
                name: program.name,
                won: round(won),
                spent: round(spent),
                balance: round(balance),
                total: round(total),
            });
        }
        return {
            ...super._buildDisplayPayload(order),
            loyaltyPrograms,
        };
    },
});
