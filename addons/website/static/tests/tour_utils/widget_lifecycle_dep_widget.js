import { registry } from "@web/core/registry";
import { browser } from "@web/core/browser/browser";
const localStorage = browser.localStorage;

odoo.loader.bus.addEventListener("module-started", (e) => {
    if (e.detail.moduleName !== "@web/public/interaction") {
        return;
    }

    const { Interaction } = e.detail.module;

    const localStorageKey = 'widgetAndWysiwygLifecycle';
    if (!localStorage.getItem(localStorageKey)) {
        localStorage.setItem(localStorageKey, '[]');
    }

    function addLifecycleStep(step) {
        const oldValue = localStorage.getItem(localStorageKey);
        const newValue = JSON.stringify(JSON.parse(oldValue).concat(step));
        localStorage.setItem(localStorageKey, newValue);
    }

    // TODO Re-evaluate: possibly became obsolete.
    class CountdownPatch extends Interaction {
        static selector = ".s_countdown";
        dynamicContent = {
            "_root": {
                // TODO Adapt naming if still needed.
                "t-att-class": () => ({ "public_widget_started": true }),
            },
        };
        // TODO Handle edit mode.
        disabledInEditableMode = false;

        start() {
            addLifecycleStep('widgetStart');
        }

        destroy() {
            addLifecycleStep('widgetStop');
        }
    }

    registry
        .category("public.interactions")
        .add("website.countdown_patch", CountdownPatch);
});
