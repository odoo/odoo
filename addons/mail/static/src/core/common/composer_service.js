import { reactive } from "@odoo/owl";
import { registry } from "@web/core/registry";

export const composerService = {
    dependencies: ["mail.store", "legacy_multi_tab"],
    /**
     * Enable Html composer with: odoo.__WOWL_DEBUG__.root.env.services["mail.composer"].setHtmlComposer()
     * @param {import("@web/env").OdooEnv}
     * @param {Partial<import("services").Services>} services
     */
    start(env, { legacy_multi_tab }) {
        const state = reactive({
            htmlEnabled: legacy_multi_tab.getSharedValue("mail.html_composer.enabled", false),
            setHtmlComposer() {
                if (state.htmlEnabled) {
                    return;
                }
                state.htmlEnabled = true;
                legacy_multi_tab.setSharedValue("mail.html_composer.enabled", true);
            },
            setTextComposer() {
                if (!state.htmlEnabled) {
                    return;
                }
                state.htmlEnabled = false;
                legacy_multi_tab.setSharedValue("mail.html_composer.enabled", false);
            },
        });

        legacy_multi_tab.bus.addEventListener("shared_value_updated", ({ detail }) => {
            if (detail.key === "mail.html_composer.enabled") {
                state.htmlEnabled = JSON.parse(detail.newValue);
            }
        });

        return state;
    },
};

registry.category("services").add("mail.composer", composerService);
