import { ColorList } from "@web/core/colorlist/colorlist";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "../standard_field_props";

import { Component } from "@odoo/owl";

class KanbanColorPickerField extends Component {
    static template = "web.KanbanColorPickerField";
    static props = {
        ...standardFieldProps,
    };

    get colors() {
        return ColorList.COLORS;
    }

    selectColor(colorIndex) {
        return this.props.record.update({ [this.props.name]: colorIndex }, { save: true });
    }
}

export const kanbanColorPickerField = {
    component: KanbanColorPickerField,
    extractProps(_, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("kanban_colorpicker", kanbanColorPickerField);
