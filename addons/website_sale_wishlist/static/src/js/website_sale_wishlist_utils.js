const WISHLIST_PRODUCT_IDS_SESSION_NAME = 'wishlist_product_ids';

/**
 * Get the IDs of the products in the wishlist from the session.
 *
 * @return {Array<number>} The IDs of the products in the wishlist.
 */
function getWishlistProductIds() {
    return JSON.parse(sessionStorage.getItem(WISHLIST_PRODUCT_IDS_SESSION_NAME) || '[]');
}

/**
 * Set the IDs of the products in the wishlist in the session.
 *
 * @param {ArrayLike<number>} productIds The IDs of the products in the wishlist.
 */
function setWishlistProductIds(productIds) {
    sessionStorage.setItem(
        WISHLIST_PRODUCT_IDS_SESSION_NAME, JSON.stringify(Array.from(productIds))
    );
}

/**
 * Add the specified product to the wishlist.
 *
 * @param {number} productId
 */
function addWishlistProduct(productId) {
    const productIds = new Set(getWishlistProductIds());
    productIds.add(productId);
    setWishlistProductIds(productIds);
}

/**
 * Remove the specified product from the wishlist.
 *
 * @param {number} productId
 */
function removeWishlistProduct(productId) {
    const productIds = new Set(getWishlistProductIds());
    productIds.delete(productId);
    setWishlistProductIds(productIds);
}

/**
 * Update the visibility and quantity of the wishlist button in the navbar.
 */
function updateWishlistNavBar() {
    const wishlistProductIds = getWishlistProductIds();
    const wishButton = document.querySelector('.o_wsale_my_wish');
    if (wishButton.classList.contains('o_wsale_my_wish_hide_empty')) {
        wishButton.classList.toggle('d-none', !wishlistProductIds.length);
    }
    wishButton.querySelector('.my_wish_quantity').textContent = `${wishlistProductIds.length}`;
    const wishlistQuantity = document.querySelector('.my_wish_quantity');
    wishlistQuantity.classList.toggle('d-none', !wishlistProductIds.length);
}

export default {
    getWishlistProductIds: getWishlistProductIds,
    setWishlistProductIds: setWishlistProductIds,
    addWishlistProduct: addWishlistProduct,
    removeWishlistProduct: removeWishlistProduct,
    updateWishlistNavBar: updateWishlistNavBar,
};
