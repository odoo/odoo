
export function addToWishlistFromProductPage() {
    return [
        {
            content: "Add to wishlist",
            trigger: ".js_product button.o_add_wishlist_dyn:not(.o_in_wishlist)",
            run: "click",
        },
        {
            content: "Check that the product is in the wishlist",
            trigger: ".js_product button.o_add_wishlist_dyn.o_in_wishlist",
        },
    ];
}

export function addToWishlistFromShopPage() {
    // TODO in the future, sub-util to target buttons in specific product card.
    return [
        {
            content: "Add to wishlist",
            trigger: "#o_wsale_products_grid button.o_add_wishlist:not(.o_in_wishlist)",
            run: "click",
        },
        {
            content: "Check that the product is in the wishlist",
            trigger: "#o_wsale_products_grid button.o_add_wishlist.o_in_wishlist",
        },
    ];
}

export function goToWishlist({ quantity = 1 } = {}) {
    return {
        content: "Go to wishlist",
        trigger: `a sup.my_wish_quantity:text(${quantity})`,
        run: "click",
        expectUnloadPage: true,
    };
}

export function assertWishlistQuantity(quantity = 1) {
    return {
        content: "Check wishlist quantity",
        trigger: `a sup.my_wish_quantity:text(${quantity})`,
    };
}
