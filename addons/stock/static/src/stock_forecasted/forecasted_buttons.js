import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, markup } from "@odoo/owl";

export class ForecastedButtons extends Component {
    static template = "stock.ForecastedButtons";
    static props = {
        action: Object,
        resModel: { type: String, optional: true },
        reloadReport: Function,
    };

    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.context = this.props.action.context;
        this.productId = this.context.active_id;
        this.resModel = this.props.resModel || this.context.active_model || this.context.params?.active_model || 'product.template';
    }

    /**
     * Called when an action open a wizard. If the wizard is discarded, this
     * method does nothing, otherwise it reloads the report.
     * @param {Object | undefined} res
     */
    _onClose(res) {
        return res?.special || !res?.noReload || this.props.reloadReport();
    }

    async _onClickReplenish() {
        const context = { ...this.context };
        if (this.resModel === 'product.product') {
            context.default_product_id = this.productId;
        } else if (this.resModel === 'product.template') {
            context.default_product_tmpl_id = this.productId;
        }
        context.default_warehouse_id = this.context.warehouse_id;

        const action = {
            res_model: 'product.replenish',
            name: _t('Product Replenish'),
            type: 'ir.actions.act_window',
            views: [[false, 'form']],
            target: 'new',
            context: context,
        };
        return this.actionService.doAction(action, { onClose: this._onClose.bind(this) });
    }

    async _onClickUpdateQuantity() {
        const action = await this.orm.call(this.resModel, "action_open_quants", [[this.productId]]);
        if (action.res_model === "stock.quant") { // Quant view in inventory mode.
            action.views = [[false, "list"]];
        }
        if (action.help) {
            action.help = markup(action.help);
        }
        return this.actionService.doAction(action, { onClose: this._onClose.bind(this) });
    }
}
