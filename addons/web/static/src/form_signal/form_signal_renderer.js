import { Component, t, useProps } from "@odoo/owl";

const EDITABLE_TYPES = ["char", "text"];

export class FormSignalRenderer extends Component {
    static template = "web.FormSignalRenderer";

    props = useProps({
        /** a record of the store */
        record: t.object(),
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
        const value = this.props.record[name]();
        switch (this.props.fields[name].type) {
            case "many2one":
                return value ? value.display_name() : "";
            case "one2many":
            case "many2many":
                return (value || []).map((record) => record.display_name()).join(", ");
            default:
                return value === false || value === null || value === undefined
                    ? ""
                    : String(value);
        }
    }
}
