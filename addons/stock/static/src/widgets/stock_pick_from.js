/** @odoo-module native */
import { Component } from "@odoo/owl";
import { isTerminalState, leafPackageName } from "@stock/utils/stock_state";
import { registry } from "@web/core/registry";
import {
    buildM2OFieldDescription,
    computeM2OProps,
    Many2One,
    Many2OneField,
} from "@web/fields/relational/many2one";

export class StockPickFrom extends Component {
    static template = "stock.StockPickFrom";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            value: props.value || {
                id: false,
                display_name: this._quantDisplayName(),
            },
        };
    }

    _quantDisplayName() {
        const data = this.props.record.data;
        const parts = [data.location_id?.display_name];
        if (data.lot_id) {
            parts.push(data.lot_id?.display_name || data.lot_name);
        }
        if (data.package_id) {
            const packageName = data.package_id?.display_name;
            parts.push(
                isTerminalState(data.state)
                    ? leafPackageName(packageName)
                    : packageName,
            );
        }
        if (data.owner_id) {
            parts.push(data.owner_id?.display_name);
        }
        return parts.filter(Boolean).join(" - ");
    }
}

registry.category("fields").add("pick_from", {
    ...buildM2OFieldDescription(StockPickFrom),
    fieldDependencies: [
        { name: "location_id", type: "relation" },
        { name: "package_id", type: "relation" },
        { name: "lot_id", type: "relation" },
        { name: "lot_name", type: "char" },
        { name: "owner_id", type: "relation" },
        { name: "state", type: "selection" },
    ],
});
