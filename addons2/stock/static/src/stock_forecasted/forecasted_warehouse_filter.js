/** @odoo-module **/
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart } from "@odoo/owl";

export class ForecastedWarehouseFilter extends Component {

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
        return this.context.warehouse ?
            this.warehouses.find(w => w.id == this.context.warehouse) :
            this.warehouses[0];
    }
}

ForecastedWarehouseFilter.template = 'stock.ForecastedWarehouseFilter';
ForecastedWarehouseFilter.components = {Dropdown, DropdownItem};
ForecastedWarehouseFilter.props = {action: Object, setWarehouseInContext : Function, warehouses: Array};
