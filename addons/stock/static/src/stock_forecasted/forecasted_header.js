import { useService } from "@web/core/utils/hooks";
import { formatFloat } from "@web/views/fields/formatters";
import { Component, markup } from "@odoo/owl";

export class ForecastedHeader extends Component {
    static template = "stock.ForecastedHeader";
    static props = { docs: Object, openView: Function };

    setup(){
        this.orm = useService("orm");
        this.action = useService("action");

        this._formatFloat = (num) => formatFloat(num, { digits: this.props.docs.precision });
    }

    async _onClickInventory(){
        const productIds = this.props.docs.product_variants_ids;
        const action = await this.orm.call('product.product', 'action_open_quants', [productIds]);
        if (action.help) {
            action.help = markup(action.help);
        }
        return this.action.doAction(action);
    }

    async _onClickTransfers(type){
        const action = await this.orm.call(
            'stock.picking', this._getPickingActionMethod(type), [], {}
        );
        action.domain = [['product_id', 'in', this.props.docs.product_variants_ids]];
        if (action.help) {
            action.help = markup(action.help);
        }
        return this.action.doAction(action);
    }

    _getPickingActionMethod(type){
        const methodMap = {
            incoming: 'get_action_picking_tree_incoming',
            outgoing: 'get_action_picking_tree_outgoing',
        }
        return methodMap[type];
    }
}
