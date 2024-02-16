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
        var $old = $(`.${rowAddrClass}`).find('.card.border.border-primary');
        $old.find('.btn-addr').toggle();
        $old.addClass(cardClass);
        $old.removeClass('bg-primary border border-primary');

        var $new = $(ev.currentTarget).parent('div.one_kanban').find('.card');
        $new.find('.btn-addr').toggle();
        $new.removeClass(cardClass);
        $new.addClass('bg-primary border border-primary');

        rpc(
            '/shop/cart/update_address',
            {
                mode: $new.attr('mode'),
                partner_id: $new.attr('partner_id'),
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
