import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { PreparationDisplay } from "@pos_preparation_display/app/models/preparation_display";
import { getOnNotified } from "@point_of_sale/utils";
import { useService } from "@web/core/utils/hooks";

export const preparationDisplayService = {
    dependencies: ["orm", "bus_service", "mail.sound_effects"],
    async start(env, { orm, bus_service }) {
        const sound = env.services["mail.sound_effects"];
        const datas = await orm.call(
            "pos_preparation_display.display",
            "get_preparation_display_data",
            [[odoo.preparation_display.id]],
            {}
        );

        const preparationDisplayService = await new PreparationDisplay(
            datas,
            env,
            odoo.preparation_display.id
        ).ready;
        const onNotified = getOnNotified(bus_service, odoo.preparation_display.access_token);
        onNotified("LOAD_ORDERS", async (data) => {
            if (data.sound) {
                sound.play("notification");
            }
            preparationDisplayService.rawData.orders = await preparationDisplayService.orm.call(
                "pos_preparation_display.order",
                "get_preparation_display_order",
                [[], preparationDisplayService.id],
                {}
            );
            preparationDisplayService.processOrders();
        });
        onNotified("CHANGE_ORDER_STAGE", ({ order_id, stage_id, last_stage_change }) => {
            const order = preparationDisplayService.orders[order_id];
            clearTimeout(order.changeStageTimeout);
            order.stageId = stage_id;
            order.lastStageChange = last_stage_change;
            preparationDisplayService.resetOrderlineStatus(order, false, true);
            preparationDisplayService.filterOrders();
        });
        onNotified("CHANGE_ORDERLINE_STATUS", (lineStatus) => {
            for (const status of lineStatus) {
                if (!preparationDisplayService.orderlines[status.id]) {
                    continue;
                }
                preparationDisplayService.orderlines[status.id].todo = status.todo;
            }
        });
        bus_service.addEventListener("reconnect", () => {
            sound.play("notification");
            preparationDisplayService.getOrders();
        });
        return preparationDisplayService;
    },
};

registry.category("services").add("preparation_display", preparationDisplayService);

/**
 *
 * @returns {ReturnType<typeof preparationDisplay.start>}
 */
export function usePreparationDisplay() {
    return useState(useService("preparation_display"));
}
