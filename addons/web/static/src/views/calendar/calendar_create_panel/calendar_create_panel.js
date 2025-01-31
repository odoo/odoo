/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { FieldRow } from "./calendar_create_panel_row";

export class CalendarSuperQuickPanel extends Component {
    static template = "web.CalendarSuperQuickPanel";
    static components = { FieldRow };
    static props = {
        fields: { type: Object },
        orm: { type: Object, optional: true },
        model: { type: Object, optional: true },
        title: { type: String, optional: true },
        values: {type: Object}
    };

    setup() {
        this.state = useState({ values: {} });
    }

    get panelTitle() {
        return this.props.title || "Super Quick Create";
    }

    fieldRowProps(fieldName) {
        console.log(this.props.fields[fieldName])
        return {
            fieldName,
            fieldInfo: this.props.fields[fieldName],
            value: this.state.values[fieldName],
            onChange: this.onFieldValueChange.bind(this),
            orm: this.props.orm,
            model: this.props.model,
        };
    }

    onFieldValueChange(fieldName, newVal, raw_value) {
        console.log(raw_value)
        this.state.values[fieldName] = newVal;
        this.props.values.values[fieldName] = raw_value;
    }


}
