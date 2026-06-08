/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

class OpenDecimalPrecisionButton extends Component {
    static template = "account.OpenDecimalPrecisionButton";
    static props = { ...standardFieldProps };

    setup() {
        this.action = useService("action");
    }

    async discardAndOpen() {
        await this.props.record.discard();
        this.action.doAction("base.action_decimal_precision_form");
    }
}

registry.category("fields").add("open_decimal_precision_button", {
    component: OpenDecimalPrecisionButton,
});
