/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
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
        this.itemImgContainerEl = ev.currentTarget.closest(`${targetSelector}`);
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
        const data = await rpc("/shop/cart/update_json", {
            ...params,
            display: false,
            force_create: true,
        });
        if (
            data.cart_quantity &&
            data.cart_quantity !== parseInt(document.querySelector(".my_cart_quantity").textContent)
        ) {
            updateCartNavBar(data);
        };
        showCartNotification(this.call.bind(this), data.notification_info);
        return data;
    },
};
// TODO-visp: remove animate
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
    const myCartQuantityEl = document.querySelector(".my_cart_quantity");
    const parentLiEl = myCartQuantityEl.closest("li.o_wsale_my_cart");
    parentLiEl.classList.remove("d-none");
    myCartQuantityEl.classList.toggle("d-none", data.cart_quantity === 0);
    myCartQuantityEl.classList.add("o_mycart_zoom_animation");

    setTimeout(() => {
        if (!data.cart_quantity) {
            myCartQuantityEl.classList.add("fa", "fa-warning");
        } else {
            myCartQuantityEl.classList.remove("fa", "fa-warning");
        }
        myCartQuantityEl.setAttribute("title", data.warning);
        myCartQuantityEl.textContent = data.cart_quantity || "";
        myCartQuantityEl.classList.remove("o_mycart_zoom_animation");
    }, 300);
    const jsCartLinesEl = document.querySelector(".js_cart_lines");
    if (jsCartLinesEl) {
        const cartLinesEl = new DOMParser()
            .parseFromString(data["website_sale.cart_lines"], "text/html")
            .querySelector("#cart_products");
        jsCartLinesEl.parentNode.replaceChild(cartLinesEl, jsCartLinesEl);
    }
    if (document.querySelector("#cart_total")) {
        document.querySelector("#cart_total").outerHTML = data["website_sale.total"];
    }
    if (data.cart_ready) {
        document.querySelector("a[name='website_sale_main_button']")?.classList.remove('disabled');
    } else {
        document.querySelector("a[name='website_sale_main_button']")?.classList.add('disabled');
    }
}

function showCartNotification(callService, props, options = {}) {
    // Show the notification about the cart
    if (props.lines) {
        callService("cartNotificationService", "add", _t("Item(s) added to your cart"), {
            lines: props.lines,
            currency_id: props.currency_id,
            ...options,
        });
    }
    if (props.warning) {
        callService("cartNotificationService", "add", _t("Warning"), {
            warning: props.warning,
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
    const pageEl = this.el.querySelector(".oe_website_sale");
    const cartAlertEl = pageEl.querySelector("#data_warning");
    if (!cartAlertEl) {
        const cartAlertDivEl = document.createElement("div");
        cartAlertDivEl.className = "alert alert-danger alert-dismissible";
        cartAlertDivEl.setAttribute("role", "alert");
        cartAlertDivEl.id = "data_warning";

        const buttonEl = document.createElement("button");
        buttonEl.type = "button";
        buttonEl.className = "btn-close";
        buttonEl.setAttribute("data-bs-dismiss", "alert");

        const spanEl = document.createElement("span");

        cartAlertDivEl.appendChild(buttonEl);
        cartAlertDivEl.appendChild(spanEl);

        pageEl.prepend(cartAlertDivEl);
    }
    cartAlertEl.querySelector("span:last-child").textContent = message;
}

export default {
    animateClone: animateClone,
    updateCartNavBar: updateCartNavBar,
    cartHandlerMixin: cartHandlerMixin,
    showCartNotification: showCartNotification,
    showWarning: showWarning,
};
