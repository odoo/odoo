import { Component } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";
import publicWidget from "@web/legacy/js/public/public_widget";

import wSaleUtils from "@website_sale/js/website_sale_utils";


publicWidget.registry.websiteSaleCart = publicWidget.Widget.extend({
    selector: '#shop_cart',
    events: {
        'change input.js_quantity[data-product-id]': '_onChangeCartQuantity',
        'click .js_delete_product': '_onClickDeleteProduct',
        'click a.js_add_suggested_products': '_onClickSuggestedProduct',
    },

    /**
     * @constructor
     */
    init: function () {
        this._super.apply(this, arguments);

        this._changeCartQuantity = debounce(this._changeCartQuantity.bind(this), 500);
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     * @param {Event} ev
     */
    _onChangeCartQuantity: function (ev) {
        var $input = $(ev.currentTarget);
        if ($input.data('update_change')) {
            return;
        }
        var value = parseInt($input.val() || 0, 10);
        if (isNaN(value)) {
            value = 1;
        }
        var $dom = $input.closest('tr');
        var $dom_optional = $dom.nextUntil(':not(.optional_product.info)');
        var line_id = parseInt($input.data('line-id'), 10);
        var productIDs = [parseInt($input.data('product-id'), 10)];
        this._changeCartQuantity($input, value, $dom_optional, line_id, productIDs);
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickDeleteProduct: function (ev) {
        ev.preventDefault();
        $(ev.currentTarget).closest('.o_cart_product').find('.js_quantity').val(0).trigger('change');
    },
    /**
     * @private
     * @param {Event} ev
     */
    _onClickSuggestedProduct: function (ev) {
        $(ev.currentTarget).prev('input').val(1).trigger('change');
    },
    /**
     * @private
     */
    _changeCartQuantity: function ($input, value, $dom_optional, line_id, productIDs) {
        $($dom_optional).toArray().forEach((elem) => {
            $(elem).find('.js_quantity').text(value);
            productIDs.push($(elem).find('span[data-product-id]').data('product-id'));
        });
        $input.data('update_change', true);

        rpc('/shop/cart/update_json', {
            line_id: line_id,
            product_id: parseInt($input.data('product-id'), 10),
            set_qty: value,
            display: true,
        }).then((data) => {
            $input.data('update_change', false);
            var check_value = parseInt($input.val() || 0, 10);
            if (isNaN(check_value)) {
                check_value = 1;
            }
            if (value !== check_value) {
                $input.trigger('change');
                return;
            }
            if (!data.cart_quantity) {
                return window.location = '/shop/cart';
            }
            $input.val(data.quantity);
            $('.js_quantity[data-line-id='+line_id+']').val(data.quantity).text(data.quantity);

            wSaleUtils.updateCartNavBar(data);
            wSaleUtils.showWarning(data.notification_info.warning);
            // Hide the rental period when last rental product is removed
            // from the cart
            if (this.el.classList.contains('o_cart_contains_rental')) {
                if (!this.el.querySelector('.o_product_is_rental')) {
                    this.el.querySelector('#cart_rental_period')?.classList.add('d-none');
                }
            };
            // Propagating the change to the express checkout forms
            Component.env.bus.trigger('cart_amount_changed', [data.amount, data.minor_amount]);
        });
    },
});

export default publicWidget.registry.websiteSaleCart;
