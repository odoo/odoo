import { formatFloat } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";

export class ForecastedDetails extends Component {
    static template = "stock.ForecastedDetails";
    static props = { docs: Object, openView: Function, reloadReport: Function };

    setup() {
        this.orm = useService("orm");

        this.onHandCondition =
            this.props.docs.lines.length &&
            !this.props.docs.lines.some((line) => line.document_in || line.replenishment_filled);

        // TO Clean, Extend & Simplify : write directly on the line : rowspan = x, skip = true, tot_qty = y, ...
        // We need to apply rowspan logic on reservedOnHand lines too
        this.splittedIncomingLines = {};
        this.reservedOnHand = this.props.docs.lines.filter((line => !line.document_in && !line.reservation && !line.in_transit && line.replenishment_filled && line.document_out));
        this.reservedOnHandTotalQty = this.reservedOnHand.reduce((sum, line) => sum + line.quantity, 0);
        let j = 0;
        for(let i = 0; i < this.props.docs.lines.length-1; i++){
            const index = i-j;
            const line = this.props.docs.lines[index];
            const nextLine = this.props.docs.lines[i + 1];
            if (!((line.document_in && nextLine.document_in && line.document_in.id === nextLine.document_in.id && line.document_in._name === nextLine.document_in._name) || (this.reservedOnHand.includes(line) && this.reservedOnHand.includes(nextLine)))) {
                j = 0;
                continue;
            }
            this.splittedIncomingLines[index] = this.splittedIncomingLines[index] || {
                rowcount: 1,
                tot_qty: line.quantity,
            };
            this.splittedIncomingLines[index].rowcount += 1;
            this.splittedIncomingLines[index].tot_qty += nextLine.quantity;
            j++;
        }
        this._formatFloat = (num) => {
            return formatFloat(num, { digits: this.props.docs.precision });
        };
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

    displayReserve(line){
        return !line.in_transit && this.canReserveOperation(line);
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
