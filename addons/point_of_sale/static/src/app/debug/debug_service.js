/** @odoo-module */

import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { DebugWidget } from "./debug_widget";
import { withComputedProperties } from "@point_of_sale/utils";

const debugService = {
    dependencies: ["pos"],
    /**
     * @param {{ debug: string }} env
     * @param {object} deps
     * @param {import("@point_of_sale/app/pos_store").PosStore} deps.pos
     */
    start(env, { pos }) {
        const internalState = reactive({ widgetOpen: true });
        const state = withComputedProperties(reactive({}), [internalState, pos], {
            showWidget(internalState, pos) {
                return env.debug && pos.uiState === "READY" && internalState.widgetOpen;
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
