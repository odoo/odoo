/** @odoo-module **/

import { patch } from '@web/core/utils/patch';
import {
    ProductConfiguratorDialog
} from '@sale/js/product_configurator_dialog/product_configurator_dialog';

patch(ProductConfiguratorDialog, {
    props: {
        ...ProductConfiguratorDialog.props,
        subscriptionPlanId: { type: Number, optional: true },
    },
});

patch(ProductConfiguratorDialog.prototype, {
    _getAdditionalRpcParams() {
        const params = super._getAdditionalRpcParams();
        if (this.props.subscriptionPlanId) {
            params.plan_id = this.props.subscriptionPlanId;
        }
        return params;
    },
});
