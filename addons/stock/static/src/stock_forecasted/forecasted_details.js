import { formatFloat } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ForecastedDetails extends Component {
    static template = "stock.ForecastedDetails";
    static props = { docs: Object, openView: Function, reloadReport: Function };

    setup() {
        this.orm = useService("orm");
        this.onHandCondition = this.getOnHandCondition();
        this.state = useState({
            warehouses: Object.fromEntries((this.props.docs?.warehouses || []).map(
                w => [w.id, false]
            )),
        });
        this._formatFloat = (num) => {
            return formatFloat(num, { digits: this.props.docs.precision });
        };
    }

    getOnHandCondition() {
        const lines = this.props.docs.multiple_warehouses
            ? this.props.docs.warehouses.flatMap(w => w.lines || [])
            : this.props.docs.lines || [];
        return lines.length && !lines.some(line => line.document_in || line.replenishment_filled);
    }

    async _reserve(move_id){
        await this.orm.call(
            'stock.forecasted_product_product',
            'action_reserve_linked_picks',
            [move_id],
        );
        this.props.reloadReport();
    }

    async _unreserve(move_id){
        await this.orm.call(
            'stock.forecasted_product_product',
            'action_unreserve_linked_picks',
            [move_id],
        );
        this.props.reloadReport();
    }

    async _onClickChangePriority(modelName, record) {
        const value = record.priority == "0" ? "1" : "0";

        await this.orm.call(modelName, "write", [[record.id], { priority: value }]);
        this.props.reloadReport();
    }

    toggleFolded(warehouseId) {
        this.state.warehouses[warehouseId] = !this.state.warehouses[warehouseId];
    }

    isFolded(warehouseId) {
        return this.state.warehouses[warehouseId];
    }

    displayReserve(line){
        return this.props.docs.user_can_edit_pickings && !line.in_transit && this.canReserveOperation(line);
    }

    canReserveOperation(line){
        return line.move_out?.picking_id;
    }

    get futureVirtualAvailable() {
        return this.props.docs.virtual_available + this.props.docs.qty.in - this.props.docs.qty.out;
    }

    get freeStockLabel() {
        return _t('Free Stock');
    }

    classForLine(line) {
        const greyBackground = !line.document_in && !line.reservation &&
            (!line.in_transit && line.replenishment_filled && !line.document_out && !line.removal_date)
            ||
            (line.in_transit && !line.move_out);
        return greyBackground ? 'bg-200' : '';
    }

    should_have_grey_bg(line){

    }
}
