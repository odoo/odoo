import publicWidget from '@web/legacy/js/public/public_widget';
import { rpc } from '@web/core/network/rpc';

publicWidget.registry.addressCard = publicWidget.Widget.extend({
    selector: '.o_portal_address_card',
    events: {
        'click .o_set_as_default': '_setAsDefaultAddress',
        'click .o_remove_address': '_removeAddress',
    },

    _getCardData(card) {
        return {
            addressType: card.dataset.addressType,
            partnerId: card.dataset.partnerId,
        }
    },

    /**
     * Set the billing or delivery address by default
     *
     * @private
     * @param {Event} ev
     * @return {void}
     */
    async _setAsDefaultAddress(ev) {
        ev.preventDefault();
        const selectedCard = ev.target.closest('.card');
        const { addressType, partnerId } = this._getCardData(selectedCard);
        await rpc('/address/set_as_default', {
            address_type: addressType,
            address_id: partnerId,
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
    async _removeAddress(ev) {
        ev.preventDefault();
        const selectedCard = ev.target.closest('.card');
        const { partnerId } = this._getCardData(selectedCard);
        await rpc('/address/archive', {
            address_id: partnerId,
        });
        location.reload();
    },

});
export default publicWidget.registry.addressCard;
