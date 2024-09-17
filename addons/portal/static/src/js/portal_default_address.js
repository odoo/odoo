/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.portalAddress = publicWidget.Widget.extend({
    selector: '#address_checkout_billing, #address_checkout_shipping',
    events: {
        'click .js_set_default': '_changePortalAddress',
        'click .js_archive': '_archivePortalAddress',
    },

    /**
     * Set the billing or shipping address by default
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _changePortalAddress(ev) {
        ev.preventDefault();
        const setDefaultButton = ev.currentTarget;
        const card = setDefaultButton.closest('.card');

        const oldCard = card?.closest('.row').querySelector('.card.border.border-primary');
        if (oldCard) {
            oldCard.classList.add(card.dataset.mode === 'invoice' ? 'js_change_billing' : 'js_change_delivery');
            oldCard.classList.remove('bg-primary', 'border', 'border-primary');
            this._toggleCardButtons(oldCard, true);
        }
        card.classList.remove('js_change_billing', 'js_change_delivery');
        card.classList.add('bg-primary', 'border', 'border-primary');
        this._toggleCardButtons(card, false);
        await rpc('/address/update_address', {
            address_type: setDefaultButton.dataset.addressType,
            partner_id: setDefaultButton.dataset.partnerId,
            action: 'set_default',
        });

        location.reload();
    },

    /**
     * Archive the address
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _archivePortalAddress(ev) {
        ev.preventDefault();
        const setDefaultButton = ev.currentTarget;
        await rpc('/address/update_address', {
            address_type: setDefaultButton.dataset.addressType,
            partner_id: setDefaultButton.dataset.partnerId,
            action: 'archive',
        });

        location.reload();
    },

    _toggleCardButtons(card, show) {
        const deleteButton = card.querySelector('#delete-button');
        const defaultButton = card.querySelector('#default-button');
        if (deleteButton) {
            deleteButton.style.display = show ? 'inline-block' : 'd-none';
        }
        if (defaultButton) {
            defaultButton.style.display = show ? 'inline-block' : 'd-none';
        }
    },
});

export default publicWidget.registry.portalAddress;
