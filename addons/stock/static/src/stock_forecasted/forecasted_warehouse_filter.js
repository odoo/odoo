import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, t, useProps } from "@odoo/owl";

export class ForecastedWarehouseFilter extends Component {
    static template = "stock.ForecastedWarehouseFilter";
    static components = { Dropdown, DropdownItem };
    props = useProps({
        action: t.object(),
        setWarehouseInContext: t.function(),
        warehouses: t.array(),
    });

    setup() {
        this.orm = useService("orm");
        this.context = this.props.action.context;
        this.warehouses = this.props.warehouses;
        onWillStart(this.onWillStart)
    }

    async onWillStart() {
        this.displayWarehouseFilter = (this.warehouses.length > 1);
    }

    _onSelected(id){
        this.props.setWarehouseInContext(Number(id));
    }

    get activeWarehouse(){
        return this.context.warehouse_id ? this.warehouses.find((w) => w.id == this.context.warehouse_id) : this.warehouses[0];
    }

    get warehousesItems() {
        return this.warehouses.map(warehouse => ({
            id: warehouse.id,
            label: warehouse.name,
            onSelected: () => this._onSelected(warehouse.id),
        }));
    }
}
