import { cookie } from '@web/core/browser/cookie';

const COMPARISON_PRODUCT_IDS_COOKIE_NAME = 'comparison_product_ids';
const MAX_COMPARISON_PRODUCTS = 4;

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
 */
function setComparisonProductIds(productIds) {
    cookie.set(COMPARISON_PRODUCT_IDS_COOKIE_NAME, JSON.stringify(Array.from(productIds)));
}

/**
 * Add the specified product to the comparison.
 *
 * @param {number} productId
 */
function addComparisonProduct(productId) {
    const productIds = new Set(getComparisonProductIds());
    productIds.add(productId);
    setComparisonProductIds(productIds);
}

/**
 * Remove the specified product from the comparison.
 *
 * @param {number} productId
 */
function removeComparisonProduct(productId) {
    const productIds = new Set(getComparisonProductIds());
    productIds.delete(productId);
    setComparisonProductIds(productIds);
}

export default {
    MAX_COMPARISON_PRODUCTS: MAX_COMPARISON_PRODUCTS,
    getComparisonProductIds: getComparisonProductIds,
    setComparisonProductIds: setComparisonProductIds,
    addComparisonProduct: addComparisonProduct,
    removeComparisonProduct: removeComparisonProduct,
};
