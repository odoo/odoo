/** @odoo-module **/

import Wysiwyg from "web_editor.wysiwyg";
import { patch } from "@web/core/utils/patch";

// Duplicated from "@website/../tests/tour_utils/widget_lifecycle_dep_widget"
// Cannot be imported for some reason, probably because of this being lazy
// loaded?
function addLifecycleStep(step) {
    const localStorageKey = 'widgetAndWysiwygLifecycle';
    const oldValue = window.localStorage.getItem(localStorageKey);
    const newValue = JSON.stringify(JSON.parse(oldValue).concat(step));
    window.localStorage.setItem(localStorageKey, newValue);
}

patch(Wysiwyg.prototype, "widget_lifecycle_patch_wysiwyg.wysiwyg", {
    /**
     * @override
     */
    async start() {
        addLifecycleStep('wysiwygStart');
        await this._super(...arguments);
        addLifecycleStep('wysiwygStarted');
    },
    /**
     * @override
     */
    destroy() {
        addLifecycleStep('wysiwygStop');
        this._super(...arguments);
    },
});
