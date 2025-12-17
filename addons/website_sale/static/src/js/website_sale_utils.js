import { markup } from '@odoo/owl';
import { browser } from '@web/core/browser/browser';
import { cookie } from '@web/core/browser/cookie';
import { _t } from '@web/core/l10n/translation';
import { setElementContent } from '@web/core/utils/html';

const COMPARISON_PRODUCT_IDS_COOKIE_NAME = 'comparison_product_ids';
const MAX_COMPARISON_PRODUCTS = 4;
const COMPARISON_EVENT = 'comparison_products_changed'

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
    cartLines[0]?.insertAdjacentHTML('beforebegin', markup(data['website_sale.cart_lines']));
    cartLines.forEach(el => el.remove());

    updateCartSummary(data);

    // Adjust the cart's left column width to accommodate the cart summary (right column). The left
    // column of an empty cart initially takes the full width, but adding products (e.g. via quick
    // reorder) enables the cart summary on the right.
    document.querySelector('.oe_cart').classList.toggle('col-lg-7', !!data.cart_quantity);

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
    if (!message) return;
    document.querySelector('.oe_website_sale')?.querySelector('#data_warning')?.remove();

    const alertDiv = document.createElement('div');
    alertDiv.classList.add('alert', 'alert-danger', 'alert-dismissible');
    alertDiv.role = 'alert';
    alertDiv.id = 'data_warning';
    const closeButton = document.createElement('button');
    closeButton.classList.add('btn-close');
    closeButton.type = 'button'; // Avoid default submit type in case of a form.
    closeButton.dataset.bsDismiss = 'alert';
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    alertDiv.appendChild(closeButton);
    alertDiv.appendChild(messageSpan);
    document.querySelector('.oe_website_sale').prepend(alertDiv);
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

// COMPARISON PRODUCTS UTILITIES

/**
 * Get the IDs of the products to compare from the cookie.
 *
 * @return {Array<number>} The IDs of the products to compare.
 */
function getComparisonProductIds() {
    return JSON.parse(cookie.get(COMPARISON_PRODUCT_IDS_COOKIE_NAME) || '[]');
}

/**
 * Set the IDs of the products to compare in the cookie.
 *
 * @param {ArrayLike<number>} productIds The IDs of the products to compare.
 * @param {EventBus} bus
 */
function setComparisonProductIds(productIds, bus) {
    cookie.set(COMPARISON_PRODUCT_IDS_COOKIE_NAME, JSON.stringify(Array.from(productIds)));
    notifyComparisonListeners(bus);
}

/**
 * Add the specified product to the comparison.
 *
 * @param {number} productId
 * @param {EventBus} bus
 */
function addComparisonProduct(productId, bus) {
    const productIds = new Set(getComparisonProductIds());
    productIds.add(productId);
    setComparisonProductIds(productIds, bus);
}

/**
 * Remove the specified product from the comparison.
 *
 * @param {number} productId
 * @param {EventBus} bus
 */
function removeComparisonProduct(productId, bus) {
    const productIds = new Set(getComparisonProductIds());
    productIds.delete(productId);
    setComparisonProductIds(productIds, bus);
}

/**
 * Clear all products in comparison list
 *
 * @param {EventBus} bus
 */
function clearComparisonProducts(bus) {
    const productIds = getComparisonProductIds();
    cookie.delete(COMPARISON_PRODUCT_IDS_COOKIE_NAME);
    notifyComparisonListeners(bus);
    enableDisabledProducts(productIds);
}

/**
 * Notify comparison listeners using an event bus that the values of productshave changed
 *
 * @param {EventBus} bus
 */
function notifyComparisonListeners(bus) {
    if (bus) {
        bus.dispatchEvent(new CustomEvent(COMPARISON_EVENT, { bubbles: true }));
    }
}

/**
 * After removing products from comparison, update the disabled button
 */
function enableDisabledProducts(productIds) {
    for (const productId of productIds) {
        const productCompareButton = document.querySelector(
            `.o_add_compare[data-product-product-id="${productId}"]`
        );
        if (productCompareButton) {
            updateDisabled(productCompareButton, false);
        }
    }
}

/**
 * Update the disabled/enabled state of an element.
 *
 * @param {Element} el The element to disable/enable.
 * @param {boolean} isDisabled Whether the element should be disabled.
 */
function updateDisabled(el, isDisabled) {
    el.disabled = isDisabled;
    el.classList.toggle('disabled', isDisabled);
}

export default {
    updateCartNavBar: updateCartNavBar,
    showWarning: showWarning,
    getSelectedAttributeValues: getSelectedAttributeValues,
    updateQuickReorderSidebar: updateQuickReorderSidebar,
    updateDisabled: updateDisabled,
    MAX_COMPARISON_PRODUCTS: MAX_COMPARISON_PRODUCTS,
    COMPARISON_EVENT: COMPARISON_EVENT,
    getComparisonProductIds: getComparisonProductIds,
    setComparisonProductIds: setComparisonProductIds,
    addComparisonProduct: addComparisonProduct,
    removeComparisonProduct: removeComparisonProduct,
    clearComparisonProducts: clearComparisonProducts,
    notifyComparisonListeners: notifyComparisonListeners,
    enableDisabledProducts: enableDisabledProducts,
};
