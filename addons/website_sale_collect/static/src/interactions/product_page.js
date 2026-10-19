import { patch } from '@web/core/utils/patch';
import { ProductPage } from '@website_sale/interactions/product_page';

patch(ProductPage.prototype, {
    /**
     * Override of `website_sale` to trigger a state update of the ClickAndCollectAvailability
     * component when the combination info is updated.
     *
     * @param {Event} ev
     * @param {Element} parent
     * @param {Object} combination
     */
    async _onChangeCombination(ev, parent, combination) {
        await super._onChangeCombination(...arguments);
        this.env.bus.trigger('updateCombinationInfo', combination);
    },
});
