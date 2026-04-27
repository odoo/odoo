/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class MoveReversed extends Component {
    static template = "account_asset.moveReversed";
    static props = {...standardFieldProps};
}

export const moveReversed = {
    component: MoveReversed,
};

registry.category("fields").add("deprec_lines_reversed", moveReversed);
