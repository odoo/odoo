/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { Many2OneField, many2OneField } from '@web/views/fields/many2one/many2one_field';

export class ProjectMany2OneField extends Many2OneField {
    static template = "project.ProjectMany2OneField";
    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        const { record } = this.props;
        if (!record.data.project_id && !record._isRequired("project_id")) {
            props.placeholder = _t("Private");
        }
        return props;
    }
}

export const projectMany2OneField = {
    ...many2OneField,
    component: ProjectMany2OneField,
    fieldDependencies: [
        ...(many2OneField.fieldDependencies || []),
    ],
};

registry.category("fields").add("project", projectMany2OneField);
