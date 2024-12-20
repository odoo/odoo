import { WebsiteSale } from '@website_sale/js/website_sale';

WebsiteSale.include({
    /**
     * Toggles the add to cart button depending on the possibility of the
     * current combination.
     *
     * @override
     */
    _toggleDisable: function (parent, isCombinationPossible) {
        this._super(...arguments);
        parent.querySelector("a.a-submit").classList.toggle("disabled", !isCombinationPossible);
    },
});
