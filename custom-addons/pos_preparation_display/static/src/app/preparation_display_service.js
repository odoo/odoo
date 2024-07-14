/** @odoo-module **/
import { useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { PreparationDisplay } from "@pos_preparation_display/app/models/preparation_display";
import { useService } from "@web/core/utils/hooks";

export const preparationDisplayService = {
    dependencies: ["orm", "bus_service", "sound"],
    async start(env, { orm, bus_service, sound }) {
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

        bus_service.addChannel(`preparation_display-${odoo.preparation_display.access_token}`);
        bus_service.addEventListener("reconnect", () => {
            sound.play("notification");
            return preparationDisplayService.getOrders();
        });
        bus_service.addEventListener("notification", async (message) => {
            const proms = message.detail.map((detail) => {
                const datas = detail.payload;
                // We need to check if the notification is about this preparation display.
                // Currently, the webservice does not allow to filter the notifications.
                if (datas.preparation_display_id !== odoo.preparation_display.id) {
                    return false;
                }
                switch (detail.type) {
                    case "load_orders":
                        if (detail.payload.sound) {
                            sound.play("notification");
                        }
                        return preparationDisplayService.getOrders();
                    case "change_order_stage":
                        return preparationDisplayService.wsMoveToNextStage(
                            datas.order_id,
                            datas.stage_id,
                            datas.last_stage_change
                        );
                    case "change_orderline_status":
                        return preparationDisplayService.wsChangeLinesStatus(datas.status);
                }
            });

            await Promise.all(proms);
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
