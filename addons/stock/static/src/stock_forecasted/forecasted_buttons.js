/** @odoo-module **/
import { useService } from "@web/core/utils/hooks";
const { Component} = owl;

export class ForecastedButtons extends Component {

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.context = this.props.action.context;
        this.productId = this.context.active_id;
        this.resModel = this.context.active_model || this.context.params.active_model || 'product.template';
    }

    async _onClickReplenish() {
        const context = { ...this.context};
        if (this.resModel === 'product.product') {
            context.default_product_id = this.productId;
        } else if (this.resModel === 'product.template') {
            context.default_product_tmpl_id = this.productId;
        }
        context.default_warehouse_id = this.context.warehouse;

        const action = {
            res_model: 'product.replenish',
            name: this.env._t('Product Replenish'),
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            target: 'new',
            context: context,
        };
        return this.actionService.doAction(action, {
            onClose: (res) => {
                if (res && res.special) {
                    // Do nothing when the wizard is discarded.
                    return;
                }
                // Otherwise, reload the report.
                this.props.reloadReport();
            },
        });
    }
}

ForecastedButtons.props = {action : Object, reloadReport : Function};
ForecastedButtons.template = 'stock.ForecastedButtons';
