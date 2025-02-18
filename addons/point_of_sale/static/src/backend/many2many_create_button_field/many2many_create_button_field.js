import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useOpenMany2XRecord, useX2ManyCrud } from "@web/views/fields/relational_utils";
import { many2ManyTagsField } from "@web/views/fields/many2many_tags/many2many_tags_field";

export class Many2ManyCreateButtonField extends Component {
    static template = "point_of_sale.ManyTestField";
    static props = {
        record: { type: Object },
        string: { type: String, optional: true },
    };
    setup() {
        const list = this.props.record.data[this.props.name];
        const field = this.props.record.fields[this.props.name];
        const { saveRecord } = useX2ManyCrud(() => list, true);
        this.recordsIdsToAdd = [];
        this.openMany2xRecord = useOpenMany2XRecord({
            resModel: field.relation,
            activeActions: {
                create: true,
                createEdit: true,
                write: true,
            },
            getList: () => list,
            isToMany: true,
            onRecordSaved: async (record) => {
                await saveRecord([record.resId]);
            },
            fieldString: field.string,
        });
    }
    openDialog() {
        return this.openMany2xRecord({
            context: this.props.context,
        });
    }
}

export const many2ManyCreateButtonField = {
    ...many2ManyTagsField,
    component: Many2ManyCreateButtonField,
    additionalClasses: [""],
};

registry.category("fields").add("many2many_create_button_field", many2ManyCreateButtonField);
