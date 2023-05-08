/** @odoo-module */

// HELPERS ////////////////////////////////
// Each of the export functions below returns an array of steps
// (even those that return a single step, for consistency)

/**
 * START: product list screen
 * END: product list screen
 * @param {int[]} product_ids
 * @returns {Array}
 */
export function addProductsToCart(product_ids) {
    return product_ids
        .map((id) => [
            ...clickOnProductCard(id),
            // We should now be on the product main view screen
            ...clickOn("Add"),
            // We should now be on the product list screen
        ])
        .flat();
}

export function clickOnProductCard(product_id, { isCheck = false } = {}) {
    return [
        {
            content: `Click on the product card of Product ${product_id}`,
            trigger: `.o_self_order_item_card:has(p:contains('Product ${product_id}'))`,
            isCheck: isCheck,
        },
    ];
}

export function clickOnBackButton() {
    return [
        {
            content: "Click the navbar back button",
            trigger: "nav.o_self_order_navbar > button",
        },
    ];
}

export function clickOn(element, { isCheck = false } = {}) {
    return [
        {
            content: `Click on '${element}' button`,
            trigger: `.btn:contains('${element}')`,
            isCheck: isCheck,
        },
    ];
}
