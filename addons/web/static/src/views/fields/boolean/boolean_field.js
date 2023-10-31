/** @odoo-module **/

import { Component, useState } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useRecordObserver } from "@web/model/relational_model/utils";
import { standardFieldProps } from "../standard_field_props";

export class BooleanField extends Component {
    static template = "web.BooleanField";
    static components = { CheckBox };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.state = useState({});
        useRecordObserver((record) => {
            this.state.value = record.data[this.props.name];
        });
    }

    updateValue(value) {
        this.state.value = value;
        return this.props.record.update({ [this.props.name]: value });
    }

    onClick() {
        if (!this.props.readonly) {
            return this.updateValue(!this.props.record.data[this.props.name]);
        }
    }

    /**
     * @param {boolean} newValue
     */
    onChange(newValue) {
        return this.updateValue(newValue);
    }
}

export class ListBooleanField extends BooleanField {
    static template = "web.ListBooleanField";

    async onClick() {
        if (!this.props.readonly && this.props.record.isInEdition) {
            const changes = { [this.props.name]: !this.props.record.data[this.props.name] };
            await this.props.record.update(changes);
        }
    }
}

export const booleanField = {
    component: BooleanField,
    displayName: _t("Checkbox"),
    supportedTypes: ["boolean"],
    isEmpty: () => false,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("boolean", booleanField);
