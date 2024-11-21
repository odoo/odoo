import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
import { standardFieldProps } from "../standard_field_props";
import { formatSelection } from "../formatters";

import { Component } from "@odoo/owl";

export class LabelSelectionField extends Component {
    static template = "web.LabelSelectionField";
    static props = {
        ...standardFieldProps,
        classesObj: { type: Object, optional: true },
    };
    static defaultProps = {
        classesObj: {},
    };

    get className() {
        return this.props.classesObj[this.props.record.data[this.props.name]] || "primary";
    }
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
