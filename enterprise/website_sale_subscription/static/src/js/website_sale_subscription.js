/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({

    /**
     * Assign the subscription plan to the rootProduct for subscription products.
     *
     * @override
     */
    _updateRootProduct($form, productId, productTemplateId) {
        this._super(...arguments);
        const selected_plan = $form.find('.product_price .plan_select').val()
            ?? $form.find('#add_to_cart').attr('data-subscription-plan-id');
        if (selected_plan) {
            Object.assign(this.rootProduct, {
                plan_id: parseInt(selected_plan),
            });
        }
    },

    _handleAdd($form) {
        $form.find('.plan_select > option').each(function() {
            this.disabled = !this.selected;
        })
        return this._super(...arguments);
    },

    /**
     * Update the renting text when the combination change.
     * @override
     */
    _onChangeCombination: function (){
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationSubscription.apply(this, arguments);
    },
});
