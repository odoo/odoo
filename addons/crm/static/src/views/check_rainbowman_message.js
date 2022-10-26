/** @odoo-module **/

import { useService } from "@web/core/utils/hooks";

const { useComponent } = owl;

export async function checkRainbowmanMessage(orm, effect, recordId) {
    const message = await orm.call("crm.lead", "get_rainbowman_message", [[recordId]]);
    if (message) {
        effect.add({
            message,
            type: "rainbow_man",
        });
    }
}

export function useCheckRainbowman() {
    const component = useComponent();
    const orm = useService("orm");
    const effect = useService("effect");
    return checkRainbowmanMessage.bind(component, orm, effect);
}
