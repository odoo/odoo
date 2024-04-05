/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";
import { rpc } from "@web/core/network/rpc";

publicWidget.registry.websiteSaleCheckout = publicWidget.Widget.extend({
    // /shop/checkout
    selector: '#shop_checkout',
    events: {
        'click .js_change_billing': '_onClickChangeBilling',
        'click .js_change_shipping': '_onClickChangeShipping',
        'click .js_edit_address': '_onClickEditAddress',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onClickChangeBilling: function (ev) {
        this._onClickChangeAddress(ev, 'all_billing', 'js_change_billing');
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickChangeShipping: function (ev) {
        this._onClickChangeAddress(ev, 'all_shipping', 'js_change_shipping');
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickChangeAddress: function (ev, rowAddrClass, cardClass) {
        const old = document.querySelector(`.${rowAddrClass}`).querySelector('.card.border.border-primary');
        let btnAddr = old.querySelector('.btn-addr');
        btnAddr.style.display = btnAddr.style.display === 'none' ? '' : 'none';
        old.classList.add(cardClass);
        old.classList.remove('bg-primary border border-primary');

        const newCardEl = ev.currentTarget.closest('div.one_kanban').querySelector('.card');
        const newBtnAddr = newCardEl.querySelector('.btn-addr');
        newBtnAddr.style.display = btnAddr.style.display === 'none' ? '' : 'none';
        newCardEl.classList.remove(cardClass);
        newCardEl.classList.add('bg-primary border border-primary');

        rpc(
            '/shop/cart/update_address',
            {
                mode: newCardEl.getAttribute('mode'),
                partner_id: newCardEl.getAttribute('partner_id'),
            }
        )
    },

    /**
     * @private
     * @param {Event} ev
     */
    _onClickEditAddress: function (ev) {
        // Do not trigger _onClickChangeBilling or _onClickChangeShipping when customer
        // clicks on the pencil to update the address
        ev.stopPropagation();
    },
});

export default publicWidget.registry.websiteSaleCheckout;
