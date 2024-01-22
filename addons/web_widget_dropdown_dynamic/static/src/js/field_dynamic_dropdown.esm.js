/** @odoo-module **/
import core from "web.core";
import {registry} from "@web/core/registry";
import {standardFieldProps} from "@web/views/fields/standard_field_props";
import {Component} from "@odoo/owl";

var _lt = core._lt;

export class FieldDynamicDropdown extends Component {
    get options() {
        var field_type = this.props.record.fields[this.props.name].type || "";
        if (["char", "integer", "selection"].includes(field_type)) {
            this._setValues();
            return this.props.record.fields[this.props.name].selection.filter(
                (option) => option[0] !== false && option[1] !== ""
            );
        }
        return [];
    }

    get value() {
        const rawValue = this.props.value;
        this.props.setDirty(false);
        return this.props.type === "many2one" && rawValue ? rawValue[0] : rawValue;
    }

    parseInteger(value) {
        return Number(value);
    }
    /**
     * @param {Event} ev
     */
    onChange(ev) {
        let lastSetValue = null;
        let isInvalid = false;
        var isDirty = ev.target.value !== lastSetValue;
        const field = this.props.record.fields[this.props.name];
        let value = JSON.parse(ev.target.value);
        if (isDirty) {
            if (value && field.type === "integer") {
                value = Number(value);
                if (!value) {
                    if (this.props.record) {
                        this.props.record.setInvalidField(this.props.name);
                    }
                    isInvalid = true;
                }
            }
            if (!isInvalid) {
                Promise.resolve(this.props.update(value));
                lastSetValue = ev.target.value;
            }
        }
        if (this.props.setDirty) {
            this.props.setDirty(isDirty);
        }
    }
    stringify(value) {
        return JSON.stringify(value);
    }

    _setValues() {
        if (this.props.record.preloadedData[this.props.name]) {
            var sel_value = this.props.record.preloadedData[this.props.name];
            // Convert string element to integer if field is integer
            if (this.props.record.fields[this.props.name].type === "integer") {
                sel_value = sel_value.map((val_updated) => {
                    return val_updated.map((e) => {
                        if (typeof e === "string" && !isNaN(Number(e))) {
                            return Number(e);
                        }
                        return e;
                    });
                });
            }
            this.props.record.fields[this.props.name].selection = sel_value;
        }
    }
}

FieldDynamicDropdown.description = _lt("Dynamic Dropdown");
FieldDynamicDropdown.template = "web.SelectionField";
FieldDynamicDropdown.legacySpecialData = "_fetchDynamicDropdownValues";
FieldDynamicDropdown.props = {
    ...standardFieldProps,
};
FieldDynamicDropdown.supportedTypes = ["char", "integer", "selection"];
registry.category("fields").add("dynamic_dropdown", FieldDynamicDropdown);
