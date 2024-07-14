/** @odoo-module **/

import VariantMixin from "@website_sale/js/sale_variant_mixin";
import publicWidget from "@web/legacy/js/public/public_widget";

import "@website_sale/js/website_sale";

/**
 * Update the renting text when the combination change.
 *
 * @param {Event} ev
 * @param {$.Element} $parent
 * @param {object} combination
 */
VariantMixin._onChangeCombinationSubscription = function (ev, $parent, combination) {
    if (!this.isWebsite || !combination.is_subscription) {
        return;
    }
    const parent = $parent.get(0);
    const unit = parent.querySelector(".o_subscription_unit");
    if (!unit) {
        return;
    }
    unit.textContent = combination.temporal_unit_display;
};

publicWidget.registry.WebsiteSale.include({
    /**
     * Update the renting text when the combination change.
     * @override
     */
    _onChangeCombination: function (){
        this._super.apply(this, arguments);
        VariantMixin._onChangeCombinationSubscription.apply(this, arguments);
    },
});

export default VariantMixin;
