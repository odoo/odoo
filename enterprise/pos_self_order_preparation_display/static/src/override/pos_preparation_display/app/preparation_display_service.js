import { preparationDisplayService } from "@pos_preparation_display/app/preparation_display_service";
import { patch } from "@web/core/utils/patch";
import { getOnNotified } from "@point_of_sale/utils";

patch(preparationDisplayService, {
    async start(env, { orm, bus_service, sound }) {
        const prepDisplay = await super.start(...arguments);
        const onNotified = getOnNotified(bus_service, odoo.preparation_display.access_token);
        onNotified("PAPER_STATUS", (posConfigChange) => {
            prepDisplay.configPaperStatus.find(
                (posConfig) => posConfig.id == posConfigChange[0].id
            ).has_paper = posConfigChange[0].has_paper;
        });
        return prepDisplay;
    },
});
