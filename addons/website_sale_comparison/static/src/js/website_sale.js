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
        parentEl?.querySelector("a.a-submit").classList.toggle("disabled", !isCombinationPossible);
    },
    /**
     * The "_onSubmitClick" method was overridden because the
     * 'aSubmitEl.closest("form").submit()' function in the "website_sale.js"
     * file submits the form without triggering the submit event. To address
     * this, we manually dispatch the event from the overridden method.
     * @override
     * @param {event} ev
     */
    _onClickSubmit(ev) {
        if(ev.currentTarget.closest("form").matches(".o_add_cart_form_compare")) {
            var aSubmitEl = ev.currentTarget;
            const event = new Event("submit");
            aSubmitEl.closest("form").dispatchEvent(event);
            return;
        }
        this._super(...arguments);
    }
});
