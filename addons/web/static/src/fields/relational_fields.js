/** @odoo-module **/
import { registry } from "@web/core/registry";
import { useModel } from "../views/helpers/model";
import { RelationalModel } from "../views/relational_model";
import { ListRenderer } from "../views/list/list_renderer";
import { ListArchParser } from "../views/list/list_view";

const { Component } = owl;

export class FieldMany2one extends Component {
    setup() {
        const data = this.props.record.data[this.props.name];
        this.data = data ? data[1] : "";
    }
}

FieldMany2one.template = "web.FieldMany2one";

registry.category("fields").add("many2one", FieldMany2one);

export class FieldMany2ManyTags extends Component {
    setup() {
        const dataList = this.props.record.data[this.props.name];
        this.data = (dataList && dataList.data) || [];
    }
}

FieldMany2ManyTags.template = "web.FieldMany2ManyTags";
FieldMany2ManyTags.fieldsToFetch = {
    display_name: { type: "char" },
};

registry.category("fields").add("many2many_tags", FieldMany2ManyTags);

export class FieldX2Many extends Component {
    static template = "web.FieldX2Many";

    setup() {
        const viewMode = this.props.viewMode || ["list"];
        const { arch, fields } = this.props.archs[viewMode[0]];
        this.fields = fields;
        const parentRecord = this.props.record;
        const fieldName = this.props.name;
        const field = parentRecord.fields[fieldName];
        const modelName = field.relation;

        this.archInfo = new ListArchParser().parse(arch, fields);
        this.model = useModel(RelationalModel, {
            resModel: modelName,
            fields: fields,
            resIds: parentRecord.data[fieldName],
            activeFields: this.archInfo.columns.map((col) => col.name),
            parentRecord,
        });
        this.Renderer = ListRenderer;
    }
}

registry.category("fields").add("one2many", FieldX2Many);
