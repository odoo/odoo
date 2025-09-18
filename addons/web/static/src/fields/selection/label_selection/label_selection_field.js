// @ts-check

/** @module @web/fields/selection/label_selection/label_selection_field - Colored label display field for Selection columns */

import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { formatSelection } from "@web/fields/formatters";
import { standardFieldProps } from "@web/fields/standard_field_props";

export class LabelSelectionField extends Component {
    static template = "web.LabelSelectionField";
    static props = {
        ...standardFieldProps,
        classesObj: { type: Object, optional: true },
    };
    static defaultProps = {
        classesObj: {},
    };

    /** @returns {string} CSS class name for the current selection value */
    get className() {
        return (
            this.props.classesObj[this.props.record.data[this.props.name]] || "primary"
        );
    }
    /** @returns {string} Formatted display label for the current selection value */
    get string() {
        return formatSelection(this.props.record.data[this.props.name], {
            selection: Array.from(this.props.record.fields[this.props.name].selection),
        });
    }
}

export const labelSelectionField = {
    component: LabelSelectionField,
    displayName: _t("Label Selection"),
    supportedOptions: [
        {
            label: _t("Classes"),
            name: "classes",
            type: "string",
        },
    ],
    supportedTypes: ["selection"],
    extractProps: ({ options }) => ({
        classesObj: options.classes,
    }),
};

registry.category("fields").add("label_selection", labelSelectionField);
