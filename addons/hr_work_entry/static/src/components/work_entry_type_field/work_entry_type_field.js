import { registry } from "@web/core/registry";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Component, onWillRender, onWillUpdateProps, useState } from "@odoo/owl";
import { Many2One } from "@web/views/fields/many2one/many2one";

export class WorkEntryType extends Component {
    static template = "hr_work_entry.WorkEntryType";
    static props = {
        data: Object,
        className: { type: String, optional: true },
    };

    setup() {
        this.state = useState({ data: this.props.data });
        onWillUpdateProps((nextProps) => {
            this.state.data = nextProps.data;
        });
    }
}

function extractData(record) {
    if (!record) {
        return null;
    }
    let name;
    if ("display_name" in record) {
        name = record.display_name;
    } else if ("name" in record) {
        name = record.name.id ? record.name.display_name : record.name;
    }
    return {
        id: record.id,
        display_name: name,
        display_code: record.display_code,
        color: record.color,
    };
}

export class WorkEntryTypeMany2One extends Many2One {
    get many2XAutocompleteProps() {
        const props = super.many2XAutocompleteProps;
        return {
            ...props,
            update: (records) => {
                const idNamePair = records && extractData(records[0]) ? records[0] : false;
                this.update(idNamePair);
            },
        };
    }
}

export class Many2OneWorkEntryTypeField extends Many2OneField {
    static template = "hr_work_entry.Many2OneWorkEntryTypeField";
    static components = {
        ...Many2OneField.components,
        Many2One: WorkEntryTypeMany2One,
        WorkEntryType,
    };

    setup() {
        super.setup();
        this.state = useState({ data: this.props.record.data });
        onWillRender(() => {
            if (this.props.record.data?.work_entry_type_id.color) {
                this.state.data = this.props.record.data.work_entry_type_id;
            } else {
                this.state.data = this.props.record.data;
            }
        });
    }

    get m2oProps() {
        const props = super.m2oProps;
        return {
            ...props,
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
