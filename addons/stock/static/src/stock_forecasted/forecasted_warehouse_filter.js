/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class ForecastedWarehouseFilter extends Component {
    static template = "stock.ForecastedWarehouseFilter";
    static components = { Dropdown, DropdownItem };
    static props = { action: Object, setWarehouseInContext: Function, warehouses: Array };

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

<<<<<<< saas-17.4
    get activeWarehouse() {
        let warehouseIds = null;
        if (Array.isArray(this.context.warehouse_id)) {
            warehouseIds = this.context.warehouse_id;
        } else {
            warehouseIds = [this.context.warehouse_id];
||||||| 562e053de5b0265d255df49d6f20140247d76740
    get activeWarehouse() {
        let warehouseIds = null;
        if (Array.isArray(this.context.warehouse)) {
            warehouseIds = this.context.warehouse;
        } else {
            warehouseIds = [this.context.warehouse];
=======
    get activeWarehouse(){
        let warehouseId = null;
        if (Array.isArray(this.context.warehouse)) {
            const validWarehouseIds = this.context.warehouse.filter(Number.isInteger);
            warehouseId = validWarehouseIds.length ? validWarehouseIds[0] : null;
        } else if (Number.isInteger(this.context.warehouse)) {
            warehouseId = this.context.warehouse;
>>>>>>> f2b65aa9a8ca39dc5b12a2c9e6681a05a23aa131
        }
<<<<<<< saas-17.4
        return warehouseIds
            ? this.warehouses.find((w) => warehouseIds.includes(w.id))
            : this.warehouses[0];
||||||| 562e053de5b0265d255df49d6f20140247d76740
        return warehouseIds ?
            this.warehouses.find(w => warehouseIds.includes(w.id)) :
            this.warehouses[0];
=======
        return warehouseId ? this.warehouses.find((w) => w.id == warehouseId) : this.warehouses[0];
>>>>>>> f2b65aa9a8ca39dc5b12a2c9e6681a05a23aa131
    }

    get warehousesItems() {
        return this.warehouses.map(warehouse => ({
            id: warehouse.id,
            label: warehouse.name,
            onSelected: () => this._onSelected(warehouse.id),
        }));
    }
}
