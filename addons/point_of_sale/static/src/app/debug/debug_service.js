/** @odoo-module */

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DebugWidget } from "./debug_widget";
import { withComputedProperties } from "@point_of_sale/utils";

const debugService = {
    /**
     * @param {{ debug: string }} env
     */
    start(env) {
        const internalState = reactive({ widgetOpen: true });
        const state = withComputedProperties(reactive({}), [internalState], {
            showWidget(internalState) {
                return env.debug && internalState.widgetOpen;
            },
        });
        registry.category("main_components").add("DebugWidget", {
            Component: DebugWidget,
            props: { state },
        });
        return {
            toggleWidget() {
                internalState.widgetOpen = !internalState.widgetOpen;
            },
        };
    },
};

registry.category("services").add("debug", debugService);
