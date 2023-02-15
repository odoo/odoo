/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";

const { Component } = owl;

export class ForecastedHeader extends Component{
    setup(){
        this.orm = useService("orm");
        this.action = useService("action");

        this._formatFloat = (num) => formatFloat(num, { digits: this.props.docs.precision });
    }

    async _onClickInventory(){
        const context = this._getActionContext();
        const action = await this.orm.call('stock.quant', 'action_view_quants', [], { context });
        return this.action.doAction(action);
    }

    _getActionContext(){
        const context = { ...this.context };
        const templates = this.props.docs.product_templates_ids;
        if (templates) {
            context.search_default_product_tmpl_id = templates;
        } else {
            context.search_default_product_id = this.props.docs.product_variants_ids;
        }
        return context;
    }
}
ForecastedHeader.template = 'stock.ForecastedHeader';
ForecastedHeader.props = {docs: Object, openView: Function};
