/** @odoo-module */

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

const { onWillStart} = owl;

export class StockPickFrom extends Many2OneField {
    setup() {
        super.setup();
        this.user = useService('user');
        onWillStart(async () => {
            const testedGroup = [['location', 'stock.group_stock_multi_locations'], ['lot', 'stock.group_production_lot']];
            const userGroups = await Promise.all(
                testedGroup.map((group) => this.user.hasGroup(group[1]))
            );
            this.enabledGroups = {};
            for (const [index, group] of testedGroup.entries()) {
                this.enabledGroups[group[0]] = userGroups[index];
            }
        });
    }
    get displayName() {
        return super.displayName || this._quant_display_name();
    }

    get value() {
        return super.value || [0, this._quant_display_name()];
    }

    _quant_display_name() {
        let name_parts = [];
        if (this.props.record.data.id) {
            // if location group is activated
            if (this.enabledGroups?.location) {
                name_parts.push(this.props.record.data.location_id?.[1])
            }
            if (this.enabledGroups?.lot) {
                name_parts.push(this.props.record.data.lot_id?.[1] || this.props.record.data.lot_name)
            }
            return name_parts.join(" - ");
        }
        return "";
    }
}

export const stockPickFrom = {
    ...many2OneField,
    component: StockPickFrom,
};

registry.category("fields").add("pick_from", stockPickFrom);
