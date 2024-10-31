/** @odoo-module **/
import { browser } from "@web/core/browser/browser";
const localStorage = browser.localStorage;

import publicWidget from "web.public.widget";

const localStorageKey = 'widgetAndWysiwygLifecycle';
if (!localStorage.getItem(localStorageKey)) {
    localStorage.setItem(localStorageKey, '[]');
}

export function addLifecycleStep(step) {
    const oldValue = localStorage.getItem(localStorageKey);
    const newValue = JSON.stringify(JSON.parse(oldValue).concat(step));
    localStorage.setItem(localStorageKey, newValue);
}

publicWidget.registry.CountdownPatch = publicWidget.Widget.extend({
    selector: ".s_countdown",
    disabledInEditableMode: false,

    /**
     * @override
     */
    async start() {
        addLifecycleStep('widgetStart');
        await this._super(...arguments);
        this.el.classList.add("public_widget_started");
    },
    /**
     * @override
     */
    destroy() {
        this.el.classList.remove("public_widget_started");
        addLifecycleStep('widgetStop');
        this._super(...arguments);
    },
});
