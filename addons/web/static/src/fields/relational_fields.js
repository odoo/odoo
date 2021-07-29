/** @odoo-module **/
import { registry } from "@web/core/registry";

const { Component } = owl;

export class FieldMany2one extends Component {
    static template = "web.FieldMany2one";

    setup() {
        const data = this.props.record.data[this.props.name];
        this.data = data ? data[1] : "";
    }
}

registry.category("fields").add("many2one", FieldMany2one);

export class FieldMany2ManyTags extends Component {
    static template = "web.FieldMany2ManyTags";

    setup() {
        const data = this.props.record.data[this.props.name];
        this.data = data ? data[1] : "";
    }
}

registry.category("fields").add("many2many_tags", FieldMany2ManyTags);
