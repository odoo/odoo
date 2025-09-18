// @ts-check

/** @module @web/fields/basic/boolean/boolean_field - Checkbox field widget for Boolean columns */

import { Component, useState } from "@odoo/owl";
import { CheckBox } from "@web/components/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { useRecordObserver } from "@web/model/relational_model/record_hooks";

export class BooleanField extends Component {
    static template = "web.BooleanField";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState(/** @type {{ value?: boolean }} */ ({}));
        useRecordObserver((record) => {
            this.state.value = record.data[this.props.name];
        });
    }

    /**
     * @param {boolean} newValue
     */
    onChange(newValue) {
        this.state.value = newValue;
        this.props.record.update({ [this.props.name]: newValue });
    }
}

export const booleanField = {
    component: BooleanField,
    displayName: _t("Checkbox"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
};

registry.category("fields").add("boolean", /** @type {any} */ (booleanField));
