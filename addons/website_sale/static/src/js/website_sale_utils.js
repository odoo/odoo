import { browser } from '@web/core/browser/browser';

function animateClone(cartEl, elem, offsetTop, offsetLeft) {
    if (!cartEl) {
        return Promise.resolve();
    }
    cartEl.classList.remove("d-none");
    const blinkEl = cartEl.querySelector(".o_animate_blink");
    blinkEl.classList.add("o_red_highlight", "o_shadow_animation");

    setTimeout(() => {
        blinkEl.classList.remove("o_shadow_animation");
    }, 500);

    setTimeout(() => {
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

            animation.onfinish = () => {
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
    browser.sessionStorage.setItem('website_sale_cart_quantity', data.cart_quantity);
    // Mobile and Desktop elements have to be updated.
    const cartQuantityElements = document.querySelectorAll('.my_cart_quantity');
    for(const cartQuantityElement of cartQuantityElements) {
        if (data.cart_quantity === 0) {
            cartQuantityElement.classList.add('d-none');
        } else {
            const cartIconElement = document.querySelector('li.o_wsale_my_cart');
            cartIconElement.classList.remove('d-none');
            cartQuantityElement.classList.remove('d-none');
            cartQuantityElement.classList.add('o_mycart_zoom_animation');
            setTimeout(() => {
                cartQuantityElement.textContent = data.cart_quantity;
                cartQuantityElement.classList.remove('o_mycart_zoom_animation');
            }, 300);
        }
    }

    const jsCartLinesEls = document.querySelectorAll(".js_cart_lines");
    if (jsCartLinesEls.length) {
        const parsedHTML = new DOMParser().parseFromString(
            data["website_sale.cart_lines"],
            "text/html"
        );
        const cartLinesEl = parsedHTML.querySelector("#cart_products");

        jsCartLinesEls.forEach((el) => {
            const newCartLinesEl = cartLinesEl.cloneNode(true);
            el.parentNode.replaceChild(newCartLinesEl, el);
        });
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
    const pageEl = document.querySelector(".oe_website_sale");
    let cartAlertEl = pageEl.querySelector("#data_warning");
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

        cartAlertEl = cartAlertDivEl;
    }
    cartAlertEl.querySelector("span:last-child").textContent = message;
}

export default {
    animateClone: animateClone,
    updateCartNavBar: updateCartNavBar,
    showWarning: showWarning,
};
