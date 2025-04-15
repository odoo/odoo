/** @odoo-module */

import { SelectionField, selectionField } from '@web/views/fields/selection/selection_field';
import { registry } from '@web/core/registry';

import { STATUS_COLORS, STATUS_COLOR_PREFIX } from '../../utils/project_utils';

export class ProjectStatusWithColorSelectionField extends SelectionField {
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

ProjectStatusWithColorSelectionField.props = {
    ...SelectionField.props,
    statusLabel: { type: String, optional: true },
};

ProjectStatusWithColorSelectionField.template = 'project.ProjectStatusWithColorSelectionField';

export const projectStatusWithColorSelectionField = {
    ...selectionField,
    component: ProjectStatusWithColorSelectionField,
    extractProps: (fieldInfo, dynamicInfo) => {
        const props = selectionField.extractProps(fieldInfo, dynamicInfo);
        props.statusLabel = fieldInfo.attrs.status_label;
        return props;
    },
};

registry.category("fields").add("status_with_color", projectStatusWithColorSelectionField);
