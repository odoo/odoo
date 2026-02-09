import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

export class ForecastedButtons extends Component {
    static template = "stock.ForecastedButtons";
    static props = {
        action: Object,
        resModel: { type: String, optional: true },
        reloadReport: Function,
    };

    setup() {
        this.actionService = useService("action");
        this.context = this.props.action.context;
        this.resModel = this.props.resModel || this.context.active_model || this.context.params?.active_model || 'product.template';
        this.productId = this.resModel === 'product.template' &&
            this.context.active_model === "product.template" &&
            this.context.variant_id ? this.context.variant_id : this.context.active_id;
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
        const isTemplate = this.resModel === "product.template" ||
          (this.context.active_model === "product.template" && !this.context.variant_id);
        if (!isTemplate) {
            context.default_product_id = this.productId;
        } else {
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
}
