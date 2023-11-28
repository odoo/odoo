/** @odoo-module */

import { registry } from "@web/core/registry";
import { Input } from "@web/core/tree_editor/tree_editor_components";

registry.category("editors").add("integer", (genericProps) => {
    const { value, update } = genericProps;

    // parsers/formatters defined in fields!
    const parseInteger = registry.category("parsers").get("integer");
    const formatInteger = registry.category("formatters").get("integer");

    function parseValue(value) {
        try {
            return parseInteger(value);
        } catch {
            return value;
        }
    }

    return {
        component: Input,
        isSupported: (value) => value === false || Number.isInteger(value),
        props: {
            value: value === false ? "" : String(value),
            update: (value) => update(parseValue(value)),
        },
        defaultValue: () => 1,
        serialize: (value) => formatInteger(value),
    };
});
