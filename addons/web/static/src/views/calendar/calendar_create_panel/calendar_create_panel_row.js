/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

/**
 * Renders a single row with a label + input widget, based on field type.
 * For many2one, we use Many2XAutocomplete in a generic way.
 */
export class FieldRow extends Component {
    static template = "my_module.CalendarSuperQuickPanelFieldRow";
    static components = { Many2XAutocomplete };
    static props = {
        fieldName: String,
        fieldInfo: Object,
        value: { type: [String, Number, Boolean, Object], optional: true },
        onChange: Function,
        orm: { type: Object, optional: true },
        model: { type: Object, optional: true },
    };

    /**
     * For convenience, let's define a few getters for detecting field type
     */
    get isMany2One() {
        return this.props.fieldInfo.type === "many2one";
    }
    get isBoolean() {
        return this.props.fieldInfo.type === "boolean";
    }
    get isFloat() {
        return this.props.fieldInfo.type === "float";
    }
    get isInteger() {
        return this.props.fieldInfo.type === "integer";
    }

    get many2XProps() {
        const displayName = (this.props.value && this.props.value.display_name) ? this.props.value.display_name : "";
        return {
            value: displayName,
            resModel: this.props.model.fields[this.props.fieldName].relation,
            fieldString: this.props.fieldInfo.string || this.props.fieldInfo.name,
            getDomain: () => this.props.fieldInfo.domain,
            update: this.onMany2XUpdate.bind(this),
            autoSelect: true,
            activeActions: {},
        };
    }

    onMany2XUpdate(recordListOrFalse) {
        console.log(recordListOrFalse)
        if (!recordListOrFalse) {
            this.triggerChange(null );
        } else {
            const [rec] = recordListOrFalse;
            const display_name = rec.display_name || rec.label || "";
            this.triggerChange({ id: rec.id, display_name }, rec.id);
        }
    }

    onInputChange(ev) {
        let newVal = ev.target.value;
        if (this.isBoolean) {
            newVal = ev.target.checked;
        } else if (this.isFloat || this.isInteger) {
            newVal = newVal ? parseFloat(newVal) : 0;
        }
        this.triggerChange(newVal, newVal);
    }

    triggerChange(newVal, raw_value) {
        this.props.onChange(this.props.fieldName, newVal, raw_value);
    }

    parseDomain(domainDef) {
        if (!domainDef) {
            return [];
        }
        if (Array.isArray(domainDef)) {
            return domainDef;
        }
        if (typeof domainDef === "string") {
            try {
                return JSON.parse(domainDef);
            } catch {
                // fallback
                return [];
            }
        }
        return [];
    }
}
