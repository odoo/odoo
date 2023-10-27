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

    /**
     * @param {boolean} newValue
     */
    onChange(newValue) {
        this.state.value = newValue;
        this.props.record.update({ [this.props.name]: newValue });
    }
}

export class ListBooleanField extends BooleanField {
    static template = "web.ListBooleanField";

    async onClick() {
        if (!this.props.readonly) {
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
};

export const listBooleanField = {
    ...booleanField,
    component: ListBooleanField,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            readonly: dynamicInfo.readonly,
        };
    },
};

registry.category("fields").add("boolean", booleanField);
registry.category("fields").add("list.boolean", listBooleanField);
