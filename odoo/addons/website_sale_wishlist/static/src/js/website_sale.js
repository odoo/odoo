/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     *
     * @override
     */
    _toggleDisable: function ($parent, isCombinationPossible) {
        this._super(...arguments);
        $parent.find('button.o_wish_add').toggleClass('disabled', !isCombinationPossible);
    },
});
