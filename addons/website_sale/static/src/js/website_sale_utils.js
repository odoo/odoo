import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import wUtils from "@website/js/utils";

export const cartHandlerMixin = {
    getRedirectOption() {
        const html = document.documentElement;
        this.stayOnPageOption = html.dataset.add2cartRedirect === '1';
    },
    getCartHandlerOptions(ev) {
        this.isBuyNow = ev.currentTarget.classList.contains('o_we_buy_now');
        const targetSelector = ev.currentTarget.dataset.animationSelector || 'img';
        this.itemImgContainerEl = ev.currentTarget.closest(`:has(${targetSelector})`);
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

function animateClone(cartEl, elem, offsetTop, offsetLeft) {
    if (!cartEl) {
        return Promise.resolve();
    }

    cartEl.classList.remove("d-none");
    const blinkEl = cartEl.querySelector(".o_animate_blink");
    blinkEl.classList.add("o_red_highlight", "o_shadow_animation");

    setTimeout(function () {
        blinkEl.classList.remove("o_shadow_animation");
    }, 500);

    setTimeout(function () {
        blinkEl.classList.remove("o_red_highlight");
    }, 2000);

    return new Promise(function (resolve, reject) {
        if (!elem) {
            resolve();
        }
        const imgtodragEl = elem.querySelector("img");
        if (imgtodragEl) {
            const imgcloneEl = imgtodragEl.cloneNode(true);
            const imgOffset = imgtodragEl.getBoundingClientRect();

            imgcloneEl.classList.remove("h-100", "w-100");
            imgcloneEl.style.top = imgOffset.top + "px";
            imgcloneEl.style.left = imgOffset.left + "px";
            imgcloneEl.classList.add("o_website_sale_animate");
            document.body.appendChild(imgcloneEl);

            imgcloneEl.style.width = imgtodragEl.offsetWidth + "px";
            imgcloneEl.style.height = imgtodragEl.offsetHeight + "px";

            const cartOffset = cartEl.getBoundingClientRect();

            const targetTop = cartOffset.top + offsetTop;
            const targetLeft = cartOffset.left + offsetLeft;
            const targetWidth = 75;
            const targetHeight = 75;

            // Animate the cloned element to the target position and size
            const animation = imgcloneEl.animate(
                [
                    {
                        top: imgOffset.top + "px",
                        left: imgOffset.left + "px",
                        width: imgtodragEl.offsetWidth + "px",
                        height: imgtodragEl.offsetHeight + "px",
                    },
                    {
                        top: targetTop + "px",
                        left: targetLeft + "px",
                        width: targetWidth + "px",
                        height: targetHeight + "px",
                    },
                ],
                {
                    duration: 500,
                    fill: "forwards",
                }
            );

            animation.onfinish = function () {
                resolve();
                imgcloneEl.remove();
            };
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
