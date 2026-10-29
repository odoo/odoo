import { Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";

//List View Widget
export class TimeTypeBadgeField extends Component {
    static template = "hr_work_entry.TimeTypeBadgeField";
    props = useProps(standardFieldProps);
}

export const timeTypeBadgeField = {
    component: TimeTypeBadgeField,
    fieldDependencies: [
        { name: "color", type: "integer" },
        { name: "display_code", type: "char" },
        { name: "display_name", type: "char" },
    ],
};
registry.category("fields").add("time_type_badge", timeTypeBadgeField);

//Form View M2O Widget
export class TimeTypeMany2One extends Many2One {
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

export class Many2OneTimeTypeField extends Component {
    static template = "hr_work_entry.Many2OneTimeTypeField";
    static components = {
        TimeTypeMany2One,
    };
    props = useProps(many2OneFieldProps);
    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            specification: { display_code: 1, color: 1 },
        };
    }

    get timeTypeData() {
        return this.props.record.data[this.props.name];
    }
}

export const many2OneTimeTypeField = {
    ...buildM2OFieldDescription(Many2OneTimeTypeField),
    relatedFields: [
        { name: "display_code", type: "char" },
        { name: "color", type: "char" },
        { name: "display_name", type: "char" },
    ],
};

registry.category("fields").add("many2one_time_type", many2OneTimeTypeField);
