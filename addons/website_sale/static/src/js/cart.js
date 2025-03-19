import { Component } from "@odoo/owl";
import { rpc } from "@web/core/network/rpc";
import { debounce } from "@web/core/utils/timing";
import { utils as uiUtils } from "@web/core/ui/ui_service";
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
        this.call('cart', 'add', {
            productTemplateId: parseInt(ev.currentTarget.dataset.productTemplateId, 10),
            productId: parseInt(ev.currentTarget.dataset.productId, 10),
            isCombo: ev.currentTarget.dataset.productType === 'combo',
        }, {
            isBuyNow: true,
        });
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

        rpc('/shop/cart/update', {
            line_id: line_id,
            product_id: parseInt($input.data('product-id'), 10),
            quantity: value,
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
            wSaleUtils.showWarning(data.warning);
            // Propagating the change to the express checkout forms
            Component.env.bus.trigger('cart_amount_changed', [data.amount, data.minor_amount]);
        });
    },
});

publicWidget.registry.websiteSaleCartNavigation = publicWidget.Widget.extend({
    selector: '.o_website_sale_checkout',

    /**
     * For mobile screens, `.o_cta_navigation_container` has an absolute position causing
     * overlapping issues with nearby divs, therefore the height of `.o_website_sale_checkout` needs
     * to include the height of the absolute div and needs to be updated every time an element on
     * the checkout is expanded (i.e. payment methods, cart summary)
     *
     * @override
     */
    start() {
        const ctaNavigation = document.querySelector('.o_cta_navigation_container')
        if (uiUtils.isSmall() && ctaNavigation) {
            const updateCheckoutHeight = () => {
                const updatedHeight = ctaNavigation.offsetTop + ctaNavigation.offsetHeight
                this.el.style.height = `${updatedHeight}px`;
            }
            this.resizeObserver = new ResizeObserver(updateCheckoutHeight);
            const paymentForm = document.getElementById('o_payment_form');
            const cartSummary = document.getElementById('o_wsale_accordion_item');
            if (paymentForm) {
                this.resizeObserver.observe(paymentForm);
            }
            if (cartSummary) {
                this.resizeObserver.observe(cartSummary);
            }
        }
    },

    /**
     * @override
     */
    destroy() {
        this.resizeObserver?.disconnect();
        super.destroy();
    },
});

export default publicWidget.registry.websiteSaleCart;
