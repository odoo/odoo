import { FieldRow } from "./calendar_create_panel_row";
import { Component, useState } from "@odoo/owl";

export class CalendarSuperQuickPanel extends Component {
    static template = "web.CalendarSuperQuickPanel";
    static components = { FieldRow };
    static props = {
        fields: { type: Object }, // e.g. { 'employee_id': {...}, 'state': {...}, ... }
        orm: {type: Object}, // needed so we can pass it down for many2one name_search
        title: { type: String, optional: true },
        onChange: { type: Function, optional: true },
        model: {type: Object}
    };

    setup() {
        console.log(this.props)
        this.state = useState({ values: {} });
    }

    get sortedFieldNames() {
        // simple alphabetical sort or some custom order
        return Object.keys(this.props.fields).sort();
    }

    get panelTitle() {
        return this.props.title || "Super Quick Create";
    }

    fieldRowProps(field){
        return {
            fieldName: field,
            fieldInfo: this.props.fields[field],
            value: this.state.values[field],
            onChange: this.onFieldValueChange,
            orm: this.props.orm,
            model: this.props.model
        }
    }

    onFieldValueChange(fieldName, newVal) {
        this.state.values[fieldName] = newVal;
        console.log(this.state)
        if (this.props.onChange) {
            this.props.onChange({ [fieldName]: newVal }, this.state.values);
        }
    }
}
