import { reactive } from "@odoo/owl";

import { registry } from "@web/core/registry";

export const composerSwitchService = {
    dependencies: ["mail.store", "multi_tab"],
    /**
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, { multi_tab }) {
        const state = reactive({
            htmlEnabled: multi_tab.getSharedValue("mail.html_composer.enabled", false),
            setComposerType(type) {
                console.log(`Switching composer to ${type}.`);
                state.htmlEnabled = type === "html";
                multi_tab.setSharedValue("mail.html_composer.enabled", state.htmlEnabled);
            },
        });
        multi_tab.bus.addEventListener("shared_value_updated", ({ detail }) => {
            if (detail.key === "mail.html_composer.enabled") {
                state.htmlEnabled = JSON.parse(detail.newValue);
            }
        });
        odoo.composerSwitch = {
            current: state.htmlEnabled ? "html" : "textarea",
            textarea: () => state.setComposerType("textarea"),
            html: () => state.setComposerType("html"),
        };
        return state;
    },
};

registry.category("services").add("mail.composer_switch_service", composerSwitchService);
