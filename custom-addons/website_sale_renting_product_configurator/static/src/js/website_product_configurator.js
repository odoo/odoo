/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * @override
     */
    _getContext() {
        const context = this._super.apply(this, arguments);
        Object.assign(context, this._getSerializedRentingDates());
        return context;
    }
});
