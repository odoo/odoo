/** @odoo-module **/

import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    events: Object.assign({}, WebsiteSale.prototype.events, {
        'change input[type="hidden"][name="product_id"]': "_onVariantChanged",
    }),
    /**
     * Override to trigger a change_product_id event on the daterange pickers.
     *
     * @override
     */
    _updateRootProduct($form, productId, productTemplateId) {
        this._super(...arguments);
        const $dateRangeRenting = $('.o_website_sale_daterange_picker');
        if ($dateRangeRenting.length) {
            $dateRangeRenting.trigger(
                'change_product_id', {product_id: productId}
            );
        }
    },
    /**
     * Override to trigger a change_product_id event for variant availabilities check.
     *
     * @override
     */
    _onVariantChanged() {
        const productIdElement = $('input[type="hidden"][name="product_id"]');
        const $dateRangeRenting = $(".o_website_sale_daterange_picker");
        if ($dateRangeRenting.length && productIdElement) {
            $dateRangeRenting.trigger("change_product_id", {
                product_id: parseInt(productIdElement.val(), 10),
            });
        }
    },

    /**
     * Override to update the renting stock availabilities.
     *
     * @override
     */
    _onRentingConstraintsChanged(event, info) {
        this._super.apply(this, arguments);
        if (info.rentingAvailabilities) {
            this.rentingAvailabilities = info.rentingAvailabilities;
        }
        if (info.preparationTime !== undefined) {
            this.preparationTime = info.preparationTime;
        }
    },
});
