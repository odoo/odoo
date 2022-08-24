odoo.define('website_sale.utils', function (require) {
'use strict';

const wUtils = require('website.utils');

const cartHandlerMixin = {
    getRedirectOption() {
        const html = document.documentElement;
        this.stayOnPageOption = html.dataset.add2cartRedirect === '1';
        this.forceDialog = html.dataset.add2cartRedirect === '2';
    },
    getCartHandlerOptions(ev) {
        this.isBuyNow = ev.currentTarget.classList.contains('o_we_buy_now');
        const targetSelector = ev.currentTarget.dataset.animationSelector || 'img';
        this.$itemImgContainer = this.$(ev.currentTarget).closest(`:has(${targetSelector})`);
    },
    /**
     * Used to add product depending on stayOnPageOption value.
     */
    addToCart(params) {
        if (this.isBuyNow) {
            params.express = true;
        } else if (this.stayOnPageOption) {
            return this._addToCartInPage(params);
        }
        return wUtils.sendRequest('/shop/cart/update', params);
    },
    /**
     * @private
     */
    _addToCartInPage(params) {
        params.force_create = true;
        return this._rpc({
            route: "/shop/cart/update_json",
            params: params,
        }).then(async data => {
            if (data.cart_quantity && (data.cart_quantity !== parseInt($(".my_cart_quantity").text()))) {
                await animateClone($('header .o_wsale_my_cart').first(), this.$itemImgContainer, 25, 40);
                updateCartNavBar(data);
            }
        });
    },
};

function animateClone($cart, $elem, offsetTop, offsetLeft) {
    if (!$cart.length) {
        return Promise.resolve();
    }
    $cart.find('.o_animate_blink').addClass('o_red_highlight o_shadow_animation').delay(500).queue(function () {
        $(this).removeClass("o_shadow_animation").dequeue();
    }).delay(2000).queue(function () {
        $(this).removeClass("o_red_highlight").dequeue();
    });
    return new Promise(function (resolve, reject) {
        var $imgtodrag = $elem.find('img').eq(0);
        if ($imgtodrag.length) {
            var $imgclone = $imgtodrag.clone()
                .offset({
                    top: $imgtodrag.offset().top,
                    left: $imgtodrag.offset().left
                })
                .removeClass()
                .addClass('o_website_sale_animate')
                .appendTo(document.body)
                .css({
                    // Keep the same size on cloned img.
                    width: $imgtodrag.width(),
                    height: $imgtodrag.height(),
                })
                .animate({
                    top: $cart.offset().top + offsetTop,
                    left: $cart.offset().left + offsetLeft,
                    width: 75,
                    height: 75,
                }, 1000, 'easeInOutExpo');

            $imgclone.animate({
                width: 0,
                height: 0,
            }, function () {
                resolve();
                $(this).detach();
            });
        } else {
            resolve();
        }
    });
}

/**
 * Updates both navbar cart
 * @param {Object} data
 */
function updateCartNavBar(data) {
    $(".my_cart_quantity")
        .parents('li.o_wsale_my_cart').removeClass('d-none').end()
        .addClass('o_mycart_zoom_animation').delay(300)
        .queue(function () {
            $(this)
                .toggleClass('fa fa-warning', !data.cart_quantity)
                .attr('title', data.warning)
                .text(data.cart_quantity || '')
                .removeClass('o_mycart_zoom_animation')
                .dequeue();
        });

    $(".js_cart_lines").first().before(data['website_sale.cart_lines']).end().remove();
    $(".js_cart_summary").first().before(data['website_sale.short_cart_summary']).end().remove();
}

/**
 * Displays `message` in an alert box at the top of the page if it's a
 * non-empty string.
 *
 * @param {string | null} message
 */
function showWarning(message) {
    if (!message) {
        return;
    }
    var $page = $('.oe_website_sale');
    var cart_alert = $page.children('#data_warning');
    if (!cart_alert.length) {
        cart_alert = $(
            '<div class="alert alert-danger alert-dismissible" role="alert" id="data_warning">' +
                '<button type="button" class="close" data-dismiss="alert">&times;</button> ' +
                '<span></span>' +
            '</div>').prependTo($page);
    }
    cart_alert.children('span:last-child').text(message);
}

return {
    animateClone: animateClone,
    updateCartNavBar: updateCartNavBar,
    cartHandlerMixin: cartHandlerMixin,
    showWarning: showWarning,
};
});
