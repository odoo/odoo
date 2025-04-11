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
}
