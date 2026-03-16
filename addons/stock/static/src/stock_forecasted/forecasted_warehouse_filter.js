import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Component } from "@odoo/owl";

export class ForecastedWarehouseFilter extends Component {
    static template = "stock.ForecastedWarehouseFilter";
    static components = { Dropdown, DropdownItem };
    static props = { action: Object, setWarehouseInContext: Function, warehouses: Array };

    setup() {
        this.context = this.props.action.context;
        this.warehouses = this.props.warehouses;
    }

    _onSelected(id){
        this.props.setWarehouseInContext(Number(id));
    }

    _truncateName(name) {
        return name.length > 25 ? `${name.slice(0, 25)}...` : name;
    }

    get activeWarehouse() {
        const warehouse = this.context.warehouse_id
            ? this.warehouses.find((w) => w.id == this.context.warehouse_id)
            : this.warehouses[0];

        return {
            ...warehouse,
            name: this._truncateName(warehouse.name),
        };
    }

    get warehousesItems() {
        return this.warehouses.map((warehouse) => ({
            id: warehouse.id,
            label: this._truncateName(warehouse.name),
            onSelected: () => this._onSelected(warehouse.id),
        }));
    }
}
