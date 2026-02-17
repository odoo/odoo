import { browser } from '@web/core/browser/browser';
import { _t } from '@web/core/l10n/translation';
import { createElementWithContent } from '@web/core/utils/html';

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

    const cartLines = document.querySelectorAll('.js_cart_lines');
    cartLines[0]?.insertAdjacentHTML('beforebegin', data['website_sale.cart_lines']);
    cartLines.forEach(el => el.remove());

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
        const newShorterCartSummaryEl = createElementWithContent(
            'div', data['website_sale.shorter_cart_summary'],
        );
        shorterCartSummaryEl.replaceWith(...newShorterCartSummaryEl.childNodes);
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
    updateCartNavBar: updateCartNavBar,
    getSelectedAttributeValues: getSelectedAttributeValues,
    updateQuickReorderSidebar: updateQuickReorderSidebar,
};
