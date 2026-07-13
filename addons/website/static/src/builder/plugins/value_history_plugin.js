import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

// TODO: shared doc

export class ValueHistoryPlugin extends Plugin {
    static id = "valueHistory";
    static dependencies = ["domObserver"];
    static shared = ["setValue"];

    setValue(el, value) {
        const oldValue = el.value;
        console.log({
            value,
            oldValue,
        });
        this.dependencies.domObserver.applyCustomMutation({
            apply: () => (el.value = value),
            revert: () => (el.value = oldValue),
        });
    }
}

registry.category("website-plugins").add(ValueHistoryPlugin.id, ValueHistoryPlugin);
registry.category("translation-plugins").add(ValueHistoryPlugin.id, ValueHistoryPlugin);
