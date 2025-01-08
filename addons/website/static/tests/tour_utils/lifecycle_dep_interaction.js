import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
const localStorage = browser.localStorage;

odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName !== "@web/public/interaction") {
        return;
    }

    const { Interaction } = e.detail.module;

    const localStorageKey = 'interactionAndWysiwygLifecycle';
    if (!localStorage.getItem(localStorageKey)) {
        localStorage.setItem(localStorageKey, '[]');
    }

    function addLifecycleStep(step) {
        const oldValue = localStorage.getItem(localStorageKey);
        const newValue = JSON.stringify(JSON.parse(oldValue).concat(step));
        localStorage.setItem(localStorageKey, newValue);
    }

    class CountdownPatch extends Interaction {
        static selector = ".s_countdown";
        dynamicContent = {
            "_root": {
                "t-att-class": () => ({
                    "interaction_started": true,
                }),
            },
        };

        start() {
            addLifecycleStep('interactionStart');
        }

        destroy() {
            addLifecycleStep('interactionStop');
        }
    }

    registry
        .category("public.interactions")
        .add("website.countdown_patch", CountdownPatch);

    registry
        .category("public.interactions.edit")
        .add("website.countdown_patch", {
            Interaction: CountdownPatch,
        });
});
