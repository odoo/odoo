/** @odoo-module **/

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Editor, getEditorInfo } from "@web/core/editors/editor";

class RangeEditor extends Component {
    static props = {
        subType: String,
        "*": true,
    };
    static components = { Editor };
    static template = "web.RangeEditor";

    update(index, newValue) {
        const result = [...this.props.value];
        result[index] = newValue;
        return this.props.update(result);
    }
}

registry.category("editors").add("range", (genericProps) => {
    const { subType } = genericProps;
    const { defaultValue } = getEditorInfo(subType, {
        ...genericProps,
        type: subType,
    });
    return {
        component: RangeEditor,
        defaultValue: () => {
            const val = defaultValue();
            return [val, val];
        },
        isSupported: (value) => Array.isArray(value) && value.length === 2,
    };
});
