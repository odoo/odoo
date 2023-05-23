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
            const testedGroup = [
                ['location', 'stock.group_stock_multi_locations'],
                ['lot', 'stock.group_production_lot'],
                ['package', 'stock.group_tracking_lot'],
                ['owner', 'stock.group_tracking_owner'],
            ];
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
            const data = this.props.record.data;
            if (this.enabledGroups?.location && data.location_id) {
                name_parts.push(data.location_id?.[1])
            }
            if (this.enabledGroups?.lot && data.lot_id) {
                name_parts.push(data.lot_id?.[1] || data.lot_name)
            }
            if (this.enabledGroups?.package && data.package_id) {
                name_parts.push(data.pachage_id?.[1])
            }
            if (this.enabledGroups?.owner&& data.owner) {
                name_parts.push(data.owner?.[1])
            }
            const result = name_parts.join(" - ");
            if (result) return result;
            return "- no data -";
        }
        return "";
    }
}

export const stockPickFrom = {
    ...many2OneField,
    component: StockPickFrom,
};

registry.category("fields").add("pick_from", stockPickFrom);
