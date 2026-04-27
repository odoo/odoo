/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    _getAdditionalDialogProps() {
        const props = this._super(...arguments);
        if (this.rootProduct.start_date && this.rootProduct.end_date) {
            props.rentalStartDate = this.rootProduct.start_date;
            props.rentalEndDate = this.rootProduct.end_date;
        }
        return props;
    },

    _getAdditionalRpcParams() {
        const params = this._super(...arguments);
        if (this.rootProduct.start_date && this.rootProduct.end_date) {
            params.start_date = this.rootProduct.start_date;
            params.end_date = this.rootProduct.end_date;
        }
        return params;
    },
});
