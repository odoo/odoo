import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.addressCard = publicWidget.Widget.extend({
    selector: '.o_portal_addresses',
    events: {
        'click .o_remove_address': '_removeAddress',
        'change #use_delivery_as_billing': '_toggleBillingAddressRow',
    },

     // #=== WIDGET LIFECYCLE ===#

     async start() {
        this.use_delivery_as_billing_toggle = document.querySelector('#use_delivery_as_billing');
        this.billingContainer = this.el.querySelector('#billing_container');
    },

    // #=== EVENT HANDLERS ===#

    /**
     * Archive the address
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _removeAddress(ev) {
        ev.preventDefault();
        await rpc('/my/address/archive', {
            partner_id: ev.currentTarget.dataset.partnerId,
        });
        location.reload();
    },

     /**
     * Show/hide the billing address row when the user toggles the 'use delivery as billing' input.
     *
     * The URLs of the "create address" buttons are updated to propagate the value of the input.
     *
     * @private
     * @param ev
     * @return {void}
     */
     async _toggleBillingAddressRow(ev) {
        const useDeliveryAsBilling = ev.target.checked;

        const addDeliveryAddressButton = this.el.querySelector(
            '.o_address_kanban_add_new[data-address-type="delivery"]'
        );
        if (addDeliveryAddressButton) {  // If `Add address` button for delivery.
            // Update the `use_delivery_as_billing` query param for a new delivery address URL.
            const addDeliveryUrl = new URL(addDeliveryAddressButton.href);
            addDeliveryUrl.searchParams.set(
                'use_delivery_as_billing', encodeURIComponent(useDeliveryAsBilling)
            );
            addDeliveryAddressButton.href = addDeliveryUrl.toString();
        }

        // Toggle the billing address row.
        if (useDeliveryAsBilling) {
            this.billingContainer.classList.add('d-none');  // Hide the billing address row.
        } else {
            this.billingContainer.classList.remove('d-none');  // Show the billing address row.
        }

    },

    // #=== GETTERS & SETTERS ===#

    /** Determine and return the selected address who card has the class rowAddrClass.
     *
     * @private
     * @param addressType - The type of the address: 'billing' or 'delivery'.
     * @return {Element}
     */
    _getSelectedAddress(addressType) {
        return this.el.querySelector(`.card.bg-primary[data-address-type="${addressType}"]`);
    },

});

export default publicWidget.registry.addressCard;
