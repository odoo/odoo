import { patch } from '@web/core/utils/patch';
import { WebsiteSale } from '@website_sale/interactions/website_sale';

patch(WebsiteSale.prototype, {
    /**
     * Override of `website_sale` to trigger a state update of the ClickAndCollectAvailability
     * component when the combination info is updated.
     *
     * @param {Event} ev
     * @param {Element} parent
     * @param {Object} combination
     */
    _onChangeCombination(ev, parent, combination) {
        super._onChangeCombination(...arguments);
        this.env.bus.trigger('updateCombinationInfo', combination);
    },
});
