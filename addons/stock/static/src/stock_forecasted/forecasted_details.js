/** @odoo-module **/
import { formatFloat } from "@web/views/fields/formatters";
import { useService } from "@web/core/utils/hooks";

const { Component} = owl;

export class ForecastedDetails extends Component{
    setup(){
        this.orm = useService("orm");

        this.onHandCondition = this.props.docs.lines && !this.props.docs.lines.some(line => line.document_in || line.replenishment_filled);

        this._formatFloat = (num) => {return formatFloat(num,{ digits: this.props.docs.precision });}
    }

    async _reserve(model, modelId){
        await this.orm.call(
            model,
            'action_assign',
            [[modelId]],
            // {modelId}
        );
        this.props.reloadReport();
    }

    async _unreserve(model, modelId){
        await this.orm.call(
            model,
            'do_unreserve',
            [[modelId]],
        );
        this.props.reloadReport();
    }

    async _onClickChangePriority(modelName, model){
        const value = model.priority == '0' ? '1':'0';

        await this.orm.call(
            modelName,
            'write',
            [[model.id], {priority : value}],
        );
        this.props.reloadReport();
    }

    displayReserve(line){
        return line.move_out && ['confirmed', 'partially_available'].includes(line.move_out.state) && line.move_out.picking_id;
    }

    get futureVirtualAvailable(){
        return this.props.docs.virtual_available + this.props.docs.qty.in - this.props.docs.qty.out;
    }
}
ForecastedDetails.template = 'stock.ForecastedDetails';
ForecastedDetails.props = {docs: Object, openView: Function, reloadReport: Function};
