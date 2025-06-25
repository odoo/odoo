/** @odoo-module */

import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";


export class StockPickFrom extends Many2OneField {
    get displayName() {
        return super.displayName || this._quant_display_name();
    }

    get value() {
        return super.value || [0, this._quant_display_name()];
    }

    _quant_display_name() {
        let name_parts = [];
        // if location group is activated
        const data = this.props.record.data;
        name_parts.push(data.location_id?.[1])
        if (data.lot_id) {
            name_parts.push(data.lot_id?.[1] || data.lot_name)
        }
        if (data.package_id) {
            name_parts.push(data.package_id?.[1])
        }
        if (data.owner) {
            name_parts.push(data.owner?.[1])
        }
        const result = name_parts.join(" - ");
        if (result) return result;
        return "";
    }
}

export const stockPickFrom = {
    ...many2OneField,
    component: StockPickFrom,
    fieldDependencies: [
        ...(many2OneField.fieldDependencies || []),
        // dependencies to build the quant display name
        { name: "location_id", type: "relation" },
        { name: "location_dest_id", type: "relation" },
        { name: "package_id", type: "relation" },
        { name: "owner_id", type: "relation" },
    ],
};

registry.category("fields").add("pick_from", stockPickFrom);
