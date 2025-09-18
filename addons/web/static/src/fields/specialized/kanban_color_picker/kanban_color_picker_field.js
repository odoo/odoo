// @ts-check

/** @module @web/fields/specialized/kanban_color_picker/kanban_color_picker_field - Inline color palette picker for kanban card color selection */

import { Component } from "@odoo/owl";
import { ColorList } from "@web/components/colorlist/colorlist";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";

class KanbanColorPickerField extends Component {
    static template = "web.KanbanColorPickerField";
    static props = standardFieldProps;

    /** @returns {number[]} Available color indices from the ColorList */
    get colors() {
        return ColorList.COLORS;
    }

    /**
     * @param {number} colorIndex Color index to set and immediately save
     * @returns {Promise}
     */
    selectColor(colorIndex) {
        return this.props.record.update(
            { [this.props.name]: colorIndex },
            { save: true },
        );
    }
}

export const kanbanColorPickerField = {
    component: KanbanColorPickerField,
    displayName: _t("Color Picker"),
    extractProps(fieldInfo, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("kanban_color_picker", kanbanColorPickerField);
