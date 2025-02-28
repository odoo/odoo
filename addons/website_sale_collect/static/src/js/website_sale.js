import { Component } from '@odoo/owl';
import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * Trigger a state update of the ClickAndCollectAvailability component when the combination info
     * is updated.
     *
     * @override
     */
    _onChangeCombination(ev, $parent, combination) {
        const res = this._super.apply(this, arguments);
        Component.env.bus.trigger('updateCombinationInfo', combination);
        return res;
    },
})
