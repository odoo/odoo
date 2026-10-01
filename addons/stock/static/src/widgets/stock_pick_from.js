import { asyncComputed, Component, useProps } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { odoomark } from "@web/core/utils/html";

import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { computeDirtyQuantsData } from "@stock/helpers/dirty_quants";

export class StockPickFrom extends Component {
    static template = "stock.StockPickFrom";
    static components = { Many2One };
    props = useProps({ ...many2OneFieldProps });

    setup() {
        this.orm = useService("orm");
        this.dirtyQuantsData = asyncComputed(() => this.loadDirtyQuantsData(), {
            initial: new Map(),
        });
    }

    async loadDirtyQuantsData() {
        const move = this.props.record._parentRecord;
        if (this.props.readonly || move?.resModel !== "stock.move" || !move.data.move_line_ids) {
            return new Map();
        }
        return computeDirtyQuantsData(this.orm, move.resId, move.data.move_line_ids);
    }

    get m2oProps() {
        const props = computeM2OProps(this.props);
        return {
            ...props,
            value: props.value || { id: 0, display_name: this._quant_display_name() },
            specification: {
                available_quantity: {},
                uom_id: { fields: { display_name: {} } },
            },
        };
    }

    quantDropdownQuantity(quant) {
        const availableQuantity =
            this.dirtyQuantsData().get(quant.id)?.available_quantity ?? quant.available_quantity;
        return odoomark(`\t--${availableQuantity} ${quant.uom_id?.display_name}--`);
    }

    get lotDisplayName() {
        const data = this.props.record.data;
        return data.lot_id?.display_name || data.lot_name;
    }

    _quant_display_name() {
        let name_parts = [];
        // if location group is activated
        const data = this.props.record.data;
        name_parts.push(data.location_id?.display_name);
        // name_parts.push(`${data.quantity} ${data.uom_id?.display_name}`);
        if (this.lotDisplayName) {
            name_parts.push(this.lotDisplayName);
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
        // { name: "uom_id", type: "relation" },
    ],
});
