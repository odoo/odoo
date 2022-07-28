/** @odoo-module */

import { registry } from '@web/core/registry';
import { StateSelectionField } from '@web/views/fields/state_selection/state_selection_field';

/**
 * List of colors according to the selection value, see `project_update.py`
 */
const STATUS_COLORS = {
    'on_track': 10,
    'at_risk': 2,
    'off_track': 1,
    'on_hold': 4,
};

export class StatusColorStateSelection extends StateSelectionField {
    setup() {
        super.setup();
        this.colorPrefix = 'o_status_bubble mx-0 o_color_bubble_';
        this.colors = STATUS_COLORS;
    }

    get showLabel() {
        return !this.props.hideLabel;
    }
}

registry.category('fields').add('status_with_color', StatusColorStateSelection);
