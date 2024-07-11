/** @odoo-module **/

import { registry } from "@web/core/registry";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";


export class AutoSaveSkillTypeField extends X2ManyField {
     async onAdd({ context, editable } = {}) {
        await this.props.record.model.root.save();
        await super.onAdd({ context, editable });
     }
}

export const autoSaveSkillTypeField = {
    ...x2ManyField,
    component: AutoSaveSkillTypeField,
};

registry.category("fields").add("auto_save_skill_type", autoSaveSkillTypeField);
