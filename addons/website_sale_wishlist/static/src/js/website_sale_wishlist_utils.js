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
    const wishButtons = document.querySelectorAll('.o_wsale_my_wish');
    wishButtons.forEach(button => {
        if (button.classList.contains('o_wsale_my_wish_hide_empty')) {
            button.classList.toggle('d-none', !wishlistProductIds.length);
        }
        button.querySelector('.my_wish_quantity').textContent = `${wishlistProductIds.length}`;
    });
    const wishlistQuantities = document.querySelectorAll('.my_wish_quantity');
    wishlistQuantities.forEach(quantity => {
        quantity.classList.toggle('d-none', !wishlistProductIds.length);
    });
}

function updateWishlistView() {
    const wishlistProductIDs = getWishlistProductIds();
    const wishlistEmptyEl = document.getElementById('empty-wishlist-message');
    wishlistEmptyEl.classList.toggle('d-none', wishlistProductIDs.length > 0);
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
    getWishlistProductIds: getWishlistProductIds,
    setWishlistProductIds: setWishlistProductIds,
    addWishlistProduct: addWishlistProduct,
    removeWishlistProduct: removeWishlistProduct,
    updateWishlistNavBar: updateWishlistNavBar,
    updateDisabled: updateDisabled,
    updateWishlistView: updateWishlistView,
};
