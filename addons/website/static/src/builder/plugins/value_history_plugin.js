import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } ValueHistoryShared
 * @property { ValueHistoryPlugin['setValue'] } setValue
 */

export class ValueHistoryPlugin extends Plugin {
    static id = "valueHistory";
    static dependencies = ["history"];
    static shared = ["setValue"];

    setValue(el, value) {
        const oldValue = el.value;
        this.dependencies.history.applyCustomMutation({
            apply: () => (el.value = value),
            revert: () => (el.value = oldValue),
        });
    }
}

registry.category("website-plugins").add(ValueHistoryPlugin.id, ValueHistoryPlugin);
registry.category("translation-plugins").add(ValueHistoryPlugin.id, ValueHistoryPlugin);
