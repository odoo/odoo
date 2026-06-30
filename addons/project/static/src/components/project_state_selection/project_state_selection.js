import { registry } from '@web/core/registry';
import {
    StateSelectionField,
    stateSelectionField,
} from "@web/views/fields/state_selection/state_selection_field";

import { STATUS_COLORS, STATUS_COLOR_PREFIX } from '../../utils/project_utils';

export class ProjectStateSelectionField extends StateSelectionField {
    setup() {
        super.setup();
        this.colorPrefix = STATUS_COLOR_PREFIX;
        this.colors = STATUS_COLORS;
    }

    /**
     * @override
     */
    get options() {
        return super.options.filter(o => o[0] !== 'to_define');
    }
}

export const projectStateSelectionField = {
    ...stateSelectionField,
    component: ProjectStateSelectionField,
};

registry.category("fields").add("project_state_selection", projectStateSelectionField);
