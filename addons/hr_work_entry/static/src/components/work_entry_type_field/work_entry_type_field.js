import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";

//List View Widget
export class WorkEntryTypeBadgeField extends Component {
    static template = "hr_work_entry.WorkEntryTypeBadgeField";
    props = useProps(standardFieldProps);
}

export const workEntryTypeBadgeField = {
    component: WorkEntryTypeBadgeField,
    fieldDependencies: [
        { name: "color", type: "integer" },
        { name: "display_code", type: "char" },
        { name: "name", type: "char" },
    ],
};
registry.category("fields").add("work_entry_type_badge", workEntryTypeBadgeField);

//Form View M2O Widget
export class WorkEntryTypeMany2One extends Many2One {
    /**
     * @override
     */
    get many2XAutocompleteProps() {
        const props = super.many2XAutocompleteProps;
        return {
            ...props,
            update: async (records) => {
                let record = records?.[0];
                if (
                    record?.id &&
                    (record.display_name === undefined ||
                        record.display_code === undefined ||
                        record.color === undefined)
                ) {
                    [record] = await this.orm.read(
                        this.props.relation,
                        [record.id],
                        ["display_name", "display_code", "color"]
                    );
                }
                return this.update(record || false);
            },
        };
    }
}

export class Many2OneWorkEntryTypeField extends Component {
    static template = "hr_work_entry.Many2OneWorkEntryTypeField";
    static components = {
        WorkEntryTypeMany2One,
    };
    props = useProps(many2OneFieldProps);
    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            specification: { display_code: 1, color: 1 },
        };
    }

    get workEntryTypeData() {
        return this.props.record.data[this.props.name];
    }
}

export const many2OneWorkEntryTypeField = {
    ...buildM2OFieldDescription(Many2OneWorkEntryTypeField),
    relatedFields: [
        { name: "display_code", type: "char" },
        { name: "color", type: "char" },
    ],
};

registry.category("fields").add("many2one_work_entry_type", many2OneWorkEntryTypeField);
