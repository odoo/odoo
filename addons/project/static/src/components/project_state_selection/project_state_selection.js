/** @odoo-module */

import { registry } from '@web/core/registry';
import { StateSelectionField } from '@web/views/fields/state_selection/state_selection_field';

import { STATUS_COLORS, STATUS_COLOR_PREFIX } from '../../utils/project_utils';

export class ProjectStateSelectionField extends StateSelectionField {
    setup() {
        super.setup();
        this.colorPrefix = STATUS_COLOR_PREFIX;
        this.colors = STATUS_COLORS;
    }

    get showLabel() {
        return !this.props.hideLabel;
    }
}

registry.category('fields').add('project_state_selection', ProjectStateSelectionField);
