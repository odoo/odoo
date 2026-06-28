import { SelectionField, selectionField } from "@web/views/fields/selection/selection_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { registry } from "@web/core/registry";
import { props, t } from "@odoo/owl";

import { STATUS_COLORS, STATUS_COLOR_PREFIX } from "../../utils/project_utils";

export class ProjectStatusWithColorSelectionField extends SelectionField {
    // first keys inlined from SelectionField.props (still old-style, has no defaultProps)
    props = props({
        ...standardFieldProps,
        placeholder: t.string().optional(),
        required: t.boolean().optional(),
        domain: t.or([t.array(), t.function()]).optional(),
        hideIcon: t.boolean().optional(),
        hideValue: t.boolean().optional(),
        initialPadding: t.string().optional("2"),
    });

    static template = "project.ProjectStatusWithColorSelectionField";

    setup() {
        super.setup();
        this.colorPrefix = STATUS_COLOR_PREFIX;
        this.colors = STATUS_COLORS;
    }

    get currentValue() {
        return this.props.record.data[this.props.name] || this.options[0][0];
    }

    statusColor(value) {
        return this.colors[value] ? this.colorPrefix + this.colors[value] : "";
    }
}

export const projectStatusWithColorSelectionField = {
    ...selectionField,
    component: ProjectStatusWithColorSelectionField,
    extractProps: (fieldInfo, dynamicInfo) => {
        const props = selectionField.extractProps(fieldInfo, dynamicInfo);
        props.hideIcon = Boolean(fieldInfo.attrs.hide_icon);
        props.hideValue = Boolean(fieldInfo.attrs.hide_value);
        props.initialPadding = fieldInfo.attrs.initial_padding;
        return props;
    },
};

registry.category("fields").add("status_with_color", projectStatusWithColorSelectionField);
