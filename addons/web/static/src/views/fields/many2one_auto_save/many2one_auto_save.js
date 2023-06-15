/** @odoo-module **/

import { _lt } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { many2OneField, Many2OneField } from "../many2one/many2one_field";

export class Many2OneAutoSaveField extends Many2OneField {
    async updateRecord(value) {
        // Auto-save the record.
        await this.props.record.save();
        return await super.updateRecord(...arguments);
    }
}

export const many2OneAutoSaveField = {
    ...many2OneField,
    component: Many2OneAutoSaveField,
    displayName: _lt("Many2OneAutoSave"),
};

registry.category("fields").add("many2one_auto_save", many2OneAutoSaveField);
