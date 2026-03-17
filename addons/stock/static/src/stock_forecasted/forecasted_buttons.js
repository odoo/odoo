import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, t, useProps } from "@odoo/owl";

export const forecastedButtonsProps = {
    context: t.object(),
    reloadReport: t.function(),
};

export class ForecastedButtons extends Component {
    static template = "stock.ForecastedButtons";
    static propShape = forecastedButtonsProps;

    props = useProps(this.constructor.propShape);

    setup() {
        this.actionService = useService("action");
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
        const resModel = this.resModel;
        if (resModel === 'product.product') {
            context.default_product_id = this.productId;
        } else if (resModel === 'product.template') {
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

    get context() {
        return this.props.context;
    }

    get productId() {
        return this.resModel === 'product.product' ? this.context.variant_id : this.context.active_id;
    }

    get resModel() {
        return this.context.variant_id ? 'product.product' : this.context.active_model;
    }
}
