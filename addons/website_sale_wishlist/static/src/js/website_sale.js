import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     *
     * @override
     */
    _toggleDisable(parentEl, isCombinationPossible) {
        this._super(...arguments);
        parentEl
            ?.querySelector("button.o_wish_add")
            ?.classList.toggle("disabled", !isCombinationPossible);
    },
});
