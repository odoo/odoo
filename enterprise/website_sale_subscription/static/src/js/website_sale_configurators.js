/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    _getAdditionalDialogProps() {
        const props = this._super(...arguments);
        if (this.rootProduct.plan_id) {
            props.subscriptionPlanId = this.rootProduct.plan_id;
        }
        return props;
    },

    _getAdditionalRpcParams() {
        const params = this._super(...arguments);
        if (this.rootProduct.plan_id) {
            params.plan_id = this.rootProduct.plan_id;
        }
        return params;
    },
});
