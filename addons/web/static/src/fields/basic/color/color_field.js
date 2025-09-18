// @ts-check

/** @module @web/fields/basic/color/color_field - Native color picker input field for Char columns */

import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { exprToBoolean } from "@web/core/utils/format/strings";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class ColorField extends Component {
    static template = "web.ColorField";
    static props = {
        ...standardFieldProps,
        autosave: { type: Boolean, optional: true },
    };

    /** @returns {string} */
    get color() {
        return this.props.record.data[this.props.name] || "";
    }

    /** @param {Event} ev */
    onChange(ev) {
        this.props.record.update(
            { [this.props.name]: ev.target.value },
            { save: this.props.autosave },
        );
    }
}

export const colorField = {
    component: ColorField,
    supportedTypes: ["char"],
    extractProps({ viewType, options }, dynamicInfo) {
        let autosave = false;
        if ("autosave" in options) {
            autosave = exprToBoolean(options.autosave);
        } else if (["list", "kanban"].includes(viewType)) {
            autosave = true;
        }
        return {
            readonly: dynamicInfo.readonly,
            autosave,
        };
    },
};

registry.category("fields").add("color", colorField);
