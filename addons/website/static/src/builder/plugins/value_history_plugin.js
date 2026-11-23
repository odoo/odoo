import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

/**
 * @typedef { Object } ValueHistoryShared
 * @property { ValueHistoryPlugin['setValue'] } setValue
 */

/**
 * @typedef {(data: {
 *     nodeId: import("@html_editor/core/dom_reference_map_plugin").NodeId,
 *     before: string,
 *     after: string,
 * }) => void} form_value
 */

export class ValueHistoryPlugin extends Plugin {
    static id = "valueHistory";
    static dependencies = ["history", "domReferenceMap"];
    static shared = ["setValue"];

    resources = {
        history_data_properties: {
            form_value: {
                apply: ({ nodeId, after }) => {
                    this.dependencies.domReferenceMap.getNodeById(nodeId).value = after;
                },
                revert: ({ nodeId, before }) => {
                    this.dependencies.domReferenceMap.getNodeById(nodeId).value = before;
                },
            },
        },
    };

    setValue(el, value) {
        const oldValue = el.value;
        this.dependencies.history.apply("form_value", {
            nodeId: this.dependencies.domReferenceMap.register(el),
            before: oldValue,
            after: value,
        });
    }
}

registry.category("website-plugins").add(ValueHistoryPlugin.id, ValueHistoryPlugin);
registry.category("translation-plugins").add(ValueHistoryPlugin.id, ValueHistoryPlugin);
