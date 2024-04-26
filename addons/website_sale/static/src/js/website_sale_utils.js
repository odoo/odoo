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
        this.itemImgContainer = ev.currentTarget.closest(`${targetSelector}`);
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
        if (data.cart_quantity && (data.cart_quantity !== parseInt(document.querySelector(".my_cart_quantity").textContent))) {
            updateCartNavBar(data);
        };
        showCartNotification(this.call.bind(this), data.notification_info);
        return data;
    },
};

function animateClone(cart, elem, offsetTop, offsetLeft) {
    if (!cart.length) {
        return Promise.resolve();
    }

    cart.classList.remove('d-none');
    const animateBlink = cart.querySelector('.o_animate_blink');
    animateBlink.classList.add('o_red_highlight', 'o_shadow_animation');
    setTimeout(() => {
        animateBlink.classList.remove('o_shadow_animation');
    }, 500);
    setTimeout(() => {
        animateBlink.classList.remove('o_red_highlight');
    }, 2500);

    return new Promise(function (resolve, reject) {
        if(!elem) resolve();
        const imgtodrag = elem.querySelector('img');
        if (imgtodrag.length) {
            const imgclone = imgtodrag.cloneNode(true);
            imgclone.style.position = 'absolute';
            imgclone.style.top = imgtodrag.offsetTop + 'px';
            imgclone.style.left = imgtodrag.offsetLeft + 'px';
            imgclone.className = '';
            imgclone.classList.add('o_website_sale_animate');
            document.body.appendChild(imgclone);
            imgclone.style.width = imgtodrag.offsetWidth + 'px';
            imgclone.style.height = imgtodrag.offsetHeight + 'px';
            //TODO_VISP: to check if we create animate function here
            imgclone.style.transition = 'all 0.5s ease-in-out';
            imgclone.style.top = cart.offsetTop + offsetTop + 'px';
            imgclone.style.left = cart.offsetLeft + offsetLeft + 'px';
            imgclone.style.width = '75px';
            imgclone.style.height = '75px';
            // TODO-visp: remove animate
            imgclone.animate({
                width: 0,
                height: 0,
            }, function () {
                resolve();
                this.remove();
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
    let myCartQuantity = document.querySelector(".my_cart_quantity");
    let parentLi = myCartQuantity.closest('li.o_wsale_my_cart');

    parentLi.classList.remove('d-none');
    myCartQuantity.classList.toggle('d-none', data.cart_quantity === 0);
    myCartQuantity.classList.add('o_mycart_zoom_animation');

    setTimeout(() => {
        if (!data.cart_quantity) {
            myCartQuantity.classList.add('fa', 'fa-warning');
        } else {
            myCartQuantity.classList.remove('fa', 'fa-warning');
        }
        myCartQuantity.setAttribute('title', data.warning);
        myCartQuantity.textContent = data.cart_quantity || '';
        myCartQuantity.classList.remove('o_mycart_zoom_animation');
    }, 300);
    document.querySelector(".js_cart_lines")?.insertAdjacentHTML('beforebegin', data['website_sale.cart_lines']);
    document.querySelector('.js_cart_lines')?.remove();
    if (document.querySelector("#cart_total")) {
        document.querySelector("#cart_total").outerHTML = data['website_sale.total'];
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
    var page = this.el.querySelector('.oe_website_sale');
    var cart_alert = page.querySelector('#data_warning');
    if (!cart_alert.length) {
        cart_alert = markup(
            '<div class="alert alert-danger alert-dismissible" role="alert" id="data_warning">' +
                '<button type="button" class="btn-close" data-bs-dismiss="alert"></button> ' +
                '<span></span>' +
            '</div>').prepend(page);
    }
    cart_alert.querySelector('span:last-child').textContent = message;
}

export default {
    animateClone: animateClone,
    updateCartNavBar: updateCartNavBar,
    cartHandlerMixin: cartHandlerMixin,
    showCartNotification: showCartNotification,
    showWarning: showWarning,
};
