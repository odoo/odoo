import { markup } from '@odoo/owl';
import { browser } from '@web/core/browser/browser';
import { setElementContent } from '@web/core/utils/html';

function animateClone(cart, elem, offsetTop, offsetLeft) {
    if (!cart) {
        return Promise.resolve();
    }
    cart.classList.remove("d-none");

    const blinkEl = cart.querySelector(".o_animate_blink");
    blinkEl.classList.add("o_red_highlight", "o_shadow_animation");
    setTimeout(() => blinkEl.classList.remove("o_shadow_animation"), 500);
    setTimeout(() => blinkEl.classList.remove("o_red_highlight"), 2000);

    return new Promise(function (resolve, reject) {
        if (!elem) {
            return Promise.resolve();
        }
        const imgtodrag = elem.querySelector("img");
        if (imgtodrag) {
            const rect = imgtodrag.getBoundingClientRect();

            const imgClone = imgtodrag.cloneNode(true);
            imgClone.className = "o_website_sale_animate";

            Object.assign(imgClone.style, {
                position: "absolute",
                top: `${rect.top + window.scrollY}px`,
                left: `${rect.left + window.scrollX}px`,
                width: `${imgtodrag.offsetWidth}px`,
                height: `${imgtodrag.offsetHeight}px`,
                transition: "all 0.5s ease",
                zIndex: 9999,
                pointerEvents: "none",
            });

            document.body.appendChild(imgClone);

            void imgClone.offsetWidth;

            const cartRect = cart.getBoundingClientRect();
            imgClone.style.top = `${cartRect.top + window.scrollY + offsetTop}px`;
            imgClone.style.left = `${cartRect.left + window.scrollX + offsetLeft}px`;
            imgClone.style.width = "75px";
            imgClone.style.height = "75px";

            setTimeout(() => {
                imgClone.style.transition = "all 0.3s ease";
                imgClone.style.width = "0px";
                imgClone.style.height = "0px";

                setTimeout(() => {
                    imgClone.remove();
                    resolve();
                }, 300);
            }, 500);
        } else {
            resolve();
        }
    });
}

/**
 * Returns the closest product form to a given element if exists.
 * Required for product pages with full-width or no images where the "Add to cart" button can be 
 * outside of the form.
 *
 * @param { HTMLElement } element - Reference to an HTML element in the DOM.
 * @returns { HTMLFormElement|undefined }
 */
function getClosestProductForm(element){
    return element.closest('form') ?? element.closest('.js_product')?.querySelector('form');
}

/**
 * Updates both navbar cart
 * @param {Object} data
 * @return {void}
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

    const cartLines = document.querySelector(".js_cart_lines");
    if (cartLines) {
        const temp = document.createElement("div");
        temp.innerHTML = data["website_sale.cart_lines"];
        const newCartLines = temp.firstElementChild;
        cartLines.parentNode.insertBefore(newCartLines, cartLines);
        cartLines.remove();
    }

    updateCartSummary(data);

    if (data.cart_ready) {
        document.querySelector("a[name='website_sale_main_button']")?.classList.remove('disabled');
    } else {
        document.querySelector("a[name='website_sale_main_button']")?.classList.add('disabled');
    }
}

/**
 * Update the cart summary.
 *
 * @param {Object} data
 * @return {void}
 */
function updateCartSummary(data) {
    if (data['website_sale.shorter_cart_summary']) {
        const shorterCartSummaryEl = document.querySelector('.o_wsale_shorter_cart_summary');
        setElementContent(shorterCartSummaryEl, markup(data['website_sale.shorter_cart_summary']));
    }
    if (data['website_sale.total']) {
        document.querySelectorAll('div.o_cart_total').forEach(
            div => div.innerHTML = data['website_sale.total']
        );
    }
}

/**
 * Update the quick reorder side panel.
 *
 * @param {Object} data
 * @return {void}
 */
function updateQuickReorderSidebar(data) {
    const quickReorderButton  = document.getElementById('quick_reorder_button');
    document.querySelectorAll('.o_wsale_quick_reorder_line_group').forEach(el => el.remove());
    if (data['website_sale.quick_reorder_history'].trim()) {
        document.querySelector('#quick_reorder_sidebar .offcanvas-body').insertAdjacentHTML(
            'afterbegin', data['website_sale.quick_reorder_history']
        );
        quickReorderButton.removeAttribute('disabled');
    } else {
        quickReorderButton.click();
        quickReorderButton.setAttribute('disabled', 'true');
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

    const page = document.querySelector(".oe_website_sale");
    let cartAlert = page.querySelector("#data_warning");

    if (!cartAlert) {
        cartAlert = document.createElement("div");
        cartAlert.className = "alert alert-danger alert-dismissible";
        cartAlert.setAttribute("role", "alert");
        cartAlert.id = "data_warning";

        const closeButton = document.createElement("button");
        closeButton.type = "button";
        closeButton.className = "btn-close";
        closeButton.setAttribute("data-bs-dismiss", "alert");

        const span = document.createElement("span");

        cartAlert.appendChild(closeButton);
        cartAlert.appendChild(span);
        page.insertBefore(cartAlert, page.firstChild);
    }

    cartAlert.querySelector("span:last-child").textContent = message;
}

/**
 * Return the selected attribute values from the given container.
 *
 * @param {Element} container the container to look into
 */
function getSelectedAttributeValues(container) {
    return Array.from(container.querySelectorAll(
        'input.js_variant_change:checked, select.js_variant_change'
    )).map(el => parseInt(el.value));
}

export default {
    animateClone: animateClone,
    getClosestProductForm: getClosestProductForm,
    updateCartNavBar: updateCartNavBar,
    showWarning: showWarning,
    getSelectedAttributeValues: getSelectedAttributeValues,
    updateQuickReorderSidebar: updateQuickReorderSidebar,
};
