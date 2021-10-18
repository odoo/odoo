/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { Field } from "@web/fields/field";

const { Component } = owl;

export class ListRenderer extends Component {
    setup() {
        this.fields = this.props.fields;
        this.columns = this.props.info.columns;
    }

    openRecord(record) {
        this.props.openRecord(record);
    }

    toggleGroup(group) {
        group.toggle();
    }
}

ListRenderer.template = "web.ListRenderer";
ListRenderer.components = { CheckBox, Field };
