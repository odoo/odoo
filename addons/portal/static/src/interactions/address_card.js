import { Interaction } from '@web/public/interaction';
import { registry } from '@web/core/registry';
import { rpc } from '@web/core/network/rpc';

export class AddressCard extends Interaction {
    static selector = '.o_portal_addresses';
    dynamicContent = {
        '.o_remove_address': { 't-on-click.prevent': this.removeAddress },
        '#use_delivery_as_billing': { 't-on-change': this.toggleBillingAddressRow },
    };

     setup() {
        this.billingContainer = this.el.querySelector('#billing_container');
        this.addBillingAddressBtn = this.el.querySelector('.o_add_billing_address_btn');
    }

    /**
     * Archive the address.
     *
     * @param {Event} ev
     */
    async removeAddress(ev) {
        await this.waitFor(rpc('/my/address/archive', {
            partner_id: ev.currentTarget.dataset.partnerId,
        }));
        location.reload();
    }

    /**
     * Show/hide the billing address row when the user toggles the "use delivery as billing" input.
     *
     * The URLs of the "create address" buttons are updated to propagate the value of the input.
     *
     * @param {Event} ev
     */
    async toggleBillingAddressRow(ev) {
        const useDeliveryAsBilling = ev.target.checked;

        const addDeliveryAddressButton = this.el.querySelector(
            '.o_address_card_add_new[data-address-type="delivery"]'
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
        this.addBillingAddressBtn.classList.toggle('d-none', useDeliveryAsBilling);
    }
}

registry
    .category('public.interactions')
    .add('portal.address_card', AddressCard);
