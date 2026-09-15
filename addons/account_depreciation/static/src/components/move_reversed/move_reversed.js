/** @odoo-module native */
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/fields/standard_field_props";
import { _t } from "@web/core/translation";

export class MoveReversed extends Component {
    static template = "account_depreciation.moveReversed";
    static props = { ...standardFieldProps };

    get reversedTitle() {
        return _t("This move has been reversed");
    }
}

export const moveReversed = {
    component: MoveReversed,
};

registry.category("fields").add("deprec_lines_reversed", moveReversed);
