import { cookie } from '@web/core/browser/cookie';

const COMPARISON_PRODUCT_IDS_COOKIE_NAME = 'comparison_product_ids';
const MAX_COMPARISON_PRODUCTS = 4;
const COMPARISON_EVENT = 'comparison_products_changed'

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
 * Update the disabled/enabled state of an element.
 *
 * @param {Element} el The element to disable/enable.
 * @param {boolean} isDisabled Whether the element should be disabled.
 */
function updateDisabled(el, isDisabled) {
    el.disabled = isDisabled;
    el.classList.toggle('disabled', isDisabled);
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

export default {
    MAX_COMPARISON_PRODUCTS: MAX_COMPARISON_PRODUCTS,
    COMPARISON_EVENT: COMPARISON_EVENT,
    getComparisonProductIds: getComparisonProductIds,
    setComparisonProductIds: setComparisonProductIds,
    addComparisonProduct: addComparisonProduct,
    removeComparisonProduct: removeComparisonProduct,
    clearComparisonProducts: clearComparisonProducts,
    notifyComparisonListeners: notifyComparisonListeners,
    updateDisabled: updateDisabled,
    enableDisabledProducts: enableDisabledProducts,
};
