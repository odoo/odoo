/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';

patch(SaleOrderLineProductField.prototype, {
    _getAdditionalRpcParams() {
        const params = super._getAdditionalRpcParams();
        const saleOrder = this.props.record.model.root;
        if (saleOrder.data.is_subscription) {
            params.plan_id = saleOrder.data.plan_id[0];
        }
        return params;
    },

    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        const saleOrder = this.props.record.model.root;
        if (saleOrder.data.is_subscription) {
            props.subscriptionPlanId = saleOrder.data.plan_id[0];
        }
        return props;
    },
});
