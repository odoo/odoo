/** @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";
import { Field } from "@web/fields/field";

const { Component } = owl;
const { useSubEnv } = owl.hooks;

export class ListRenderer extends Component {
    setup() {
        this.fields = this.props.fields;
        this.columns = this.props.info.columns;

        if (!this.env.model) {
            useSubEnv({ model: this.props.record.model });
        }
    }

    openRecord(record) {
        this.props.openRecord(record);
    }
}

ListRenderer.template = "web.ListRenderer";
ListRenderer.components = { CheckBox, Field };
