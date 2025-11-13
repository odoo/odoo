import { _t } from "@web/core/l10n/translation";

export function addToWishlistFromProductPage() {
    return [
        {
            content: "Add to wishlist",
            trigger: "#product_detail form a.btn.o_add_wishlist_dyn:not(.disabled)",
            run: "click",
        },
        {
            content: "Check if the button is disabled",
            trigger: "#product_detail form a.btn.o_add_wishlist_dyn.disabled",
        },
    ];
}

export function addToWishlistFromShopPage() {
    // TODO in the future, sub-util to target buttons in specific product card.
    return [
        {
            content: "Add to wishlist",
            trigger: "#o_wsale_products_grid button.btn.o_add_wishlist:not(.disabled)",
            run: "click",
        },
        {
            content: "Check that the button is disabled",
            trigger: "#o_wsale_products_grid button.btn.o_add_wishlist.disabled",
        },
    ];
}

export function goToWishlist({
    quantity = 1,
    position = "bottom",
    backend = false,
} = {}) {
    return {
        content: _t("Go to wishlist"),
        trigger: `${backend ? ":iframe" : ""} a sup.my_wish_quantity:contains(/^${quantity}$/)`,
        tooltipPosition: position,
        run: "click",
        expectUnloadPage: true,
    };
}

export function assertWishlistQuantity(quantity = 1) {
    return {
        content: "Check wishlist quantity",
        trigger: `a sup.my_wish_quantity:contains(/^${quantity}$/)`,
    };
}

export function submitCouponCode(code) {
    return [
        {
            content: "Enter gift card code",
            trigger: "form[name='coupon_code'] input[name='promo']",
            run: `edit ${code}`,
        },
        {
            content: "click on 'Apply'",
            trigger: 'form[name="coupon_code"] button[type="submit"]',
            run: 'click',
            expectUnloadPage: true,
        },
    ]
}