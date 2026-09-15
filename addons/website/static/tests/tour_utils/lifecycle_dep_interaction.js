import { registry } from "@web/core/registry";

odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName !== "@web/public/interaction") {
        return;
    }

    const { Interaction } = e.detail.module;

    const localStorageKey = "interactionAndWysiwygLifecycle";
    if (!window.localStorage.getItem(localStorageKey)) {
        window.localStorage.setItem(localStorageKey, "[]");
    }

    function addLifecycleStep(step) {
        const oldValue = window.localStorage.getItem(localStorageKey);
        const newValue = JSON.stringify(JSON.parse(oldValue).concat(step));
        window.localStorage.setItem(localStorageKey, newValue);
    }

    class CountdownPatch extends Interaction {
        static selector = ".s_countdown";
        dynamicContent = {
            _root: {
                "t-att-class": () => ({
                    interaction_started: true,
                }),
            },
        };

        start() {
            addLifecycleStep("interactionStart");
        }

        destroy() {
            addLifecycleStep("interactionStop");
        }
    }

    registry.category("public.interactions").add("website.countdown_patch", CountdownPatch);

    registry.category("public.interactions.edit").add("website.countdown_patch", {
        Interaction: CountdownPatch,
    });
});
