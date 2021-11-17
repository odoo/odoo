/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "./standard_field_props";

const { Component } = owl;

class RadioField extends Component {
    setup() {
        this.id = `radio_field_${++RadioField.nextId}`;
    }

    get items() {
        if (this.props.type === "selection") {
            return this.props.record.fields[this.props.name].selection;
        } else {
            return [[0, "m2o radio"]];
        }
    }

    /**
     * @param {any} value
     */
    onChange(value) {
        if (this.props.type === "selection") {
            this.props.update(value);
        }
    }
}

Object.assign(RadioField, {
    props: {
        ...standardFieldProps,
    },
    template: "web.RadioField",
    nextId: 0,
    isEmpty() {
        return false;
    },
});

registry.category("fields").add("radio", RadioField);
