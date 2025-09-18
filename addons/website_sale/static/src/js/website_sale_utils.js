import { markup } from '@odoo/owl';
import { browser } from '@web/core/browser/browser';
import { _t } from '@web/core/l10n/translation';
import { setElementContent } from '@web/core/utils/dom/html';

/**
 * Animates a clone of the product image flying to the cart icon.
 *
 * @param {HTMLElement} cart - the cart icon element
 * @param {HTMLElement} elem - the product element containing the image
 * @param {number} offsetTop
 * @param {number} offsetLeft
 * @returns {Promise}
 */
function animateClone(cart, elem, offsetTop, offsetLeft) {
    if (!cart) {
        return Promise.resolve();
    }
    cart.classList.remove('d-none');
    const blinkEl = cart.querySelector('.o_animate_blink');
    if (blinkEl) {
        blinkEl.classList.add('o_red_highlight', 'o_shadow_animation');
        setTimeout(() => blinkEl.classList.remove('o_shadow_animation'), 500);
        setTimeout(() => blinkEl.classList.remove('o_red_highlight'), 2500);
    }
    return new Promise(function (resolve) {
        if (!elem) {
            resolve();
            return;
        }
        const imgToDrag = elem.querySelector('img');
        if (imgToDrag) {
            const imgRect = imgToDrag.getBoundingClientRect();
            const cartRect = cart.getBoundingClientRect();
            const imgClone = imgToDrag.cloneNode(true);
            imgClone.className = 'o_website_sale_animate';
            Object.assign(imgClone.style, {
                position: 'fixed',
                top: imgRect.top + 'px',
                left: imgRect.left + 'px',
                width: imgRect.width + 'px',
                height: imgRect.height + 'px',
                zIndex: '9999',
                transition: 'all 0.5s ease',
            });
            document.body.appendChild(imgClone);

            // Trigger reflow then animate
            imgClone.offsetHeight;
            Object.assign(imgClone.style, {
                top: (cartRect.top + offsetTop) + 'px',
                left: (cartRect.left + offsetLeft) + 'px',
                width: '75px',
                height: '75px',
            });

            imgClone.addEventListener('transitionend', function onEnd() {
                imgClone.removeEventListener('transitionend', onEnd);
                // Shrink to 0
                Object.assign(imgClone.style, {
                    width: '0px',
                    height: '0px',
                    transition: 'all 0.3s ease',
                });
                imgClone.addEventListener('transitionend', function onShrinkEnd() {
                    imgClone.removeEventListener('transitionend', onShrinkEnd);
                    imgClone.remove();
                    resolve();
                }, { once: true });
            }, { once: true });
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

    const cartLinesEl = document.querySelector(".js_cart_lines");
    if (cartLinesEl && data['website_sale.cart_lines']) {
        const temp = document.createElement('div');
        temp.innerHTML = data['website_sale.cart_lines'];
        cartLinesEl.replaceWith(...temp.childNodes);
    }

    updateCartSummary(data);

    // Adjust the cart's left column width to accommodate the cart summary (right column). The left
    // column of an empty cart initially takes the full width, but adding products (e.g. via quick
    // reorder) enables the cart summary on the right.
    document.querySelector('.oe_cart')?.classList.toggle('col-lg-7', !!data.cart_quantity);

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
        quickReorderButton.parentElement.title = "";
    } else {
        quickReorderButton.click();
        quickReorderButton.setAttribute('disabled', 'true');
        quickReorderButton.parentElement.title = _t("No previous products available for reorder.");
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
    const page = document.querySelector('.oe_website_sale');
    if (!page) return;
    let cartAlert = page.querySelector('#data_warning');
    if (!cartAlert) {
        cartAlert = document.createElement('div');
        cartAlert.className = 'alert alert-danger alert-dismissible';
        cartAlert.setAttribute('role', 'alert');
        cartAlert.id = 'data_warning';
        cartAlert.innerHTML =
            '<button type="button" class="btn-close" data-bs-dismiss="alert"></button> ' +
            '<span></span>';
        page.prepend(cartAlert);
    }
    const span = cartAlert.querySelector('span:last-child');
    if (span) span.textContent = message;
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
