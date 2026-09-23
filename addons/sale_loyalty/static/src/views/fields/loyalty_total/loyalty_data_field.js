/** @odoo-module native */
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/fields/standard_field_props";

import { Component, toRaw } from "@odoo/owl";

export class LoyaltyDataField extends Component {
    static template = "sale_loyalty.LoyaltyDataField";
    static props = {
        ...standardFieldProps,
    };

    get LoyaltyCardData() {
        const LoyaltyCardData = this.props.record.data[this.props.name];
        return Object.keys(LoyaltyCardData).length && toRaw(LoyaltyCardData);
    }
}

export const loyaltyDataField = {
    component: LoyaltyDataField,
};

registry.category("fields").add("loyalty_data_field", loyaltyDataField);
