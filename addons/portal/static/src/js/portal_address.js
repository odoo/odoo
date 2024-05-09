import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.portalAddress = publicWidget.Widget.extend({
    selector: '#address_checkout, #address_checkout_delivery', // Updated to include delivery addresses
    events: {
        // Addresses
        'click .js_change_portal_billing': '_changePortalBillingAddress',
        'click .js_change_portal_shipping': '_changePortalDeliveryAddress',
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Change the billing address.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _changePortalBillingAddress (ev) {
        await this._changePortalAddress(ev, 'all_billing_address', 'js_change_portal_billing');
    },

    /**
     * Change the delivery address.
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _changePortalDeliveryAddress (ev) {
        await this._changePortalAddress(ev, 'all_delivery_address', 'js_change_portal_shipping');
    },

    /**
     * Set the billing or delivery address on the order and update the corresponding card.
     *
     * @private
     * @param {Event} ev
     * @param {String} cardClass - The class of an unselected address card: 'js_change_portal_billing' for
     *                             a billing address, `js_change_portal_shipping` for a delivery one.
     * @return {void}
     */
    async _changePortalAddress(ev, rowAddrClass, cardClass) {
        const oldCard = document.querySelector(
            `.${rowAddrClass} .card.border.border-primary`
        );
        const newCard = ev.currentTarget.closest('.card'); // Ensure it gets the closest card element

        if (oldCard) {
            oldCard.classList.add(cardClass);
            oldCard.classList.remove('bg-primary', 'border', 'border-primary');
            this.toggleCardButtons(oldCard, true); // Show buttons on old card
        }

        newCard.classList.remove(cardClass);
        newCard.classList.add('bg-primary', 'border', 'border-primary');
        this.toggleCardButtons(newCard, false); // Hide buttons on new card
    },

    toggleCardButtons(card, show) {
        const deleteButton = card.querySelector('#delete-button');
        const defaultButton = card.querySelector('#default-button');
        if (deleteButton) {
            deleteButton.style.display = show ? 'inline-block' : 'none';
        }
        if (defaultButton) {
            defaultButton.style.display = show ? 'inline-block' : 'none';
        }
    },
});

export default publicWidget.registry.portalAddress;
