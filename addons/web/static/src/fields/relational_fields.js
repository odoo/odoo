/** @odoo-module **/
import { registry } from "@web/core/registry";

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
