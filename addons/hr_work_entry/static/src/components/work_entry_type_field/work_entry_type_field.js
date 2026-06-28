import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";

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
    static props = Many2OneField.props;
    get m2oProps() {
        return {
            ...computeM2OProps(this.props),
            specification: { display_code: 1, color: 1 },
        };
    }
}

export const many2OneWorkEntryTypeField = {
    ...buildM2OFieldDescription(Many2OneWorkEntryTypeField),
    fieldDependencies: [
        { name: "display_code", type: "char" },
        { name: "color", type: "char" },
    ],
};

registry.category("fields").add("many2one_work_entry_type", many2OneWorkEntryTypeField);
