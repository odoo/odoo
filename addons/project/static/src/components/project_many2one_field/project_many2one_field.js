/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { registry } from '@web/core/registry';
import { Many2OneField, many2OneField } from '@web/views/fields/many2one/many2one_field';

export class ProjectMany2OneField extends Many2OneField {
    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        const { project_id, parent_id } = this.props.record.data;
        if (!project_id && !parent_id) {
            props.placeholder = _t("Private");
        }
        return props;
    }

    get displayName() {
        const { project_id, display_in_project } = this.props.record.data;
        return project_id && !display_in_project ? "" : super.displayName;
    }

    updateRecord(value) {
        const { project_id, display_in_project } = this.props.record.data;
        if (!display_in_project && value && value[0] === project_id[0]) {
            this.props.record.update({ "display_in_project": true });
        }
        super.updateRecord(value);
    }
}
ProjectMany2OneField.template = 'project.ProjectMany2OneField';

export const projectMany2OneField = {
    ...many2OneField,
    component: ProjectMany2OneField,
    fieldDependencies: [
        ...(many2OneField.fieldDependencies || []),
        { name: "display_in_project", type: "boolean" },
    ],
};

registry.category("fields").add("project", projectMany2OneField);
