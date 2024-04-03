/** @odoo-module */

import { X2ManyField } from "@web/views/fields/x2many/x2many_field";
import { registry } from "@web/core/registry";

import { CommonSkillsListRenderer } from "../views/skills_list_renderer";


export class SkillsListRenderer extends CommonSkillsListRenderer {
    get groupBy() {
        return 'skill_type_id';
    }

    calculateColumnWidth(column) {
        if (column.name != 'skill_level_id') {
            return {
                type: 'absolute',
                value: '90px',
            }
        }

        return super.calculateColumnWidth(column);
    }
}
SkillsListRenderer.template = 'hr_skills.SkillsListRenderer';

export class SkillsX2ManyField extends X2ManyField {
    async onAdd({ context, editable } = {}) {
        const employeeId = this.props.record.resId;
        return super.onAdd({
            editable,
            context: {
                ...context,
                default_employee_id: employeeId,
            }
        });
    }
}
SkillsX2ManyField.components = {
    ...X2ManyField.components,
    ListRenderer: SkillsListRenderer,
};

registry.category("fields").add("skills_one2many", SkillsX2ManyField);
