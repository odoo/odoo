import { Component } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";

export class StockPickFrom extends Component {
    static template = "stock.StockPickFrom";
    static components = { Many2One };
    static props = { ...Many2OneField.props };

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            value: props.value || { id: 0, display_name: this._quant_display_name() },
        };
    }

    _quant_display_name() {
        let name_parts = [];
        // if location group is activated
        const data = this.props.record.data;
        name_parts.push(data.location_id?.display_name)
        if (data.lot_id) {
            name_parts.push(data.lot_id?.display_name || data.lot_name)
        }
        if (data.package_id) {
            let packageName = data.package_id?.display_name;
            if (packageName && ["done", "cancel"].includes(data.state)) {
                packageName = packageName.split(" > ").pop();
            }
            name_parts.push(packageName);
        }
        if (data.owner) {
            name_parts.push(data.owner?.display_name)
        }
        const result = name_parts.join(" - ");
        if (result) return result;
        return "";
    }
}

registry.category("fields").add("pick_from", {
    ...buildM2OFieldDescription(StockPickFrom),
    fieldDependencies: [
        // dependencies to build the quant display name
        { name: "location_id", type: "relation" },
        { name: "location_dest_id", type: "relation" },
        { name: "package_id", type: "relation" },
        { name: "owner_id", type: "relation" },
        { name: "state", type: "char" },
    ],
});
