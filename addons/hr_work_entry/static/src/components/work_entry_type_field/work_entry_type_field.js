import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";

const badgeFields = registry.category("work_entry_type_badge_fields");
badgeFields.add("display_code", { name: "display_code", type: "char" });
badgeFields.add("color", { name: "color", type: "integer" });

//List View Widget
export class WorkEntryTypeBadgeField extends Component {
    static template = "hr_work_entry.WorkEntryTypeBadgeField";
    props = useProps(standardFieldProps);
}

export const workEntryTypeBadgeField = {
    component: WorkEntryTypeBadgeField,
    fieldDependencies: () => [...badgeFields.getAll(), { name: "name", type: "char" }],
};
registry.category("fields").add("work_entry_type_badge", workEntryTypeBadgeField);

//Form View M2O Widget
export class Many2OneWorkEntryTypeField extends Component {
    static template = "hr_work_entry.Many2OneWorkEntryTypeField";
    static components = {
        Many2One,
    };
    props = useProps(many2OneFieldProps);
    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            specification: Object.fromEntries(
                badgeFields.getAll().map(({ name }) => [name, {}])
            ),
        };
    }

    get workEntryTypeData() {
        return this.props.record.data[this.props.name];
    }
}

export const many2OneWorkEntryTypeField = {
    ...buildM2OFieldDescription(Many2OneWorkEntryTypeField),
    relatedFields: () => badgeFields.getAll(),
};

registry.category("fields").add("many2one_work_entry_type", many2OneWorkEntryTypeField);
