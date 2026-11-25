import { Component, t, useProps } from "@odoo/owl";
import { displayValue } from "../fields/display_value";

const EDITABLE_TYPES = ["char", "text"];

export class SignalFormRenderer extends Component {
    static template = "web.SignalFormRenderer";

    props = useProps({
        /** a record of the store */
        record: t.object(),
        /** description of the fields, from the view: the store does not keep labels */
        fields: t.object(),
        fieldNames: t.array(t.string()),
    });

    /**
     * @param {string} name
     */
    isEditable(name) {
        const field = this.props.fields[name];
        return EDITABLE_TYPES.includes(field.type) && !field.readonly;
    }

    /**
     * @param {string} name
     */
    displayValue(name) {
        return displayValue(this.props.record[name](), this.props.fields[name]);
    }
}
