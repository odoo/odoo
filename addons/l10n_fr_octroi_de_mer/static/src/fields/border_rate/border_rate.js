/** @odoo-module **/

import { FloatField, floatField } from "@web/views/fields/float/float_field";
import { registry } from "@web/core/registry";

export class BorderRate extends FloatField {
    static template = "l10n_fr.BorderRate";
    static components = {
        FloatField,
    };

    get regionalRateProps() {
        return {
            ...this.props,
            name: "l10n_fr_regional_rate",
        };
    }
}

export const borderRate = {
    ...floatField,
    component: BorderRate,
};

registry.category("fields").add("border_rate", borderRate);
