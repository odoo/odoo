/** @odoo-module **/

import wUtils from "@website/js/utils";

export const cartHandlerMixin = {
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
    async _addToCartInPage(params) {
        const data = await this.rpc("/shop/cart/update_json", {
            ...params,
            display: false,
            force_create: true,
        });
        if (data.cart_quantity && (data.cart_quantity !== parseInt($(".my_cart_quantity").text()))) {
            updateCartNavBar(data);
            showCartNotification(this.call.bind(this), data.notification_info);
        };
        return data;
    },
};

function animateClone($cart, $elem, offsetTop, offsetLeft) {
    if (!$cart.length) {
        return Promise.resolve();
    }
    $cart.removeClass('d-none').find('.o_animate_blink').addClass('o_red_highlight o_shadow_animation').delay(500).queue(function () {
        $(this).removeClass("o_shadow_animation").dequeue();
    }).delay(2000).queue(function () {
        $(this).removeClass("o_red_highlight").dequeue();
    });
    return new Promise(function (resolve, reject) {
        if(!$elem) resolve();
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
                }, 500);

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
    sessionStorage.setItem('website_sale_cart_quantity', data.cart_quantity);
    $(".my_cart_quantity")
        .parents('li.o_wsale_my_cart').removeClass('d-none').end()
        .toggleClass('d-none', data.cart_quantity === 0)
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
    $("#cart_total").replaceWith(data['website_sale.total']);
    if (data.cart_ready) {
        document.querySelector("a[name='website_sale_main_button']")?.classList.remove('disabled');
    } else {
        document.querySelector("a[name='website_sale_main_button']")?.classList.add('disabled');
    }
}

function showCartNotification(callService, props, options = {}) {
    // Show the notification about the cart
    if (props.lines) {
        callService("cartNotificationService", "add", "Item(s) added to your cart", {
            ...props,
            ...options,
        });
    }
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
                '<button type="button" class="btn-close" data-bs-dismiss="alert">&times;</button> ' +
                '<span></span>' +
            '</div>').prependTo($page);
    }
    cart_alert.children('span:last-child').text(message);
}

export default {
    animateClone: animateClone,
    updateCartNavBar: updateCartNavBar,
    cartHandlerMixin: cartHandlerMixin,
    showCartNotification: showCartNotification,
    showWarning: showWarning,
};
