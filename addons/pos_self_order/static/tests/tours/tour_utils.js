/** @odoo-module */

// HELPERS ////////////////////////////////
// Each of the export functions below returns an array of steps
// (even those that return a single step, for consistency)

/**
 * START: product list screen
 * END: product list screen
 * @param {number[]} product_ids
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
/**
 * @param {string} selector
 * @returns {string}
 */
export function doesNotExist(selector) {
    return `body:not(:has(${selector}))`;
}

export function clickOnProductCard(
    product_id,
    { isCheck = false, isNot = false, qty = false } = {}
) {
    let productCard = `.o_self_order_item_card:contains(Product ${product_id} test)`;
    if (qty) {
        productCard = `${productCard}:has(span:contains(${qty} x ))`;
    }
    return [
        {
            content: `${isCheck ? "Test" : "Click"} the product card of Product ${product_id}${
                qty ? ` with quantity ${qty}` : ""
            }${isNot ? " (should not present)" : ""}`,
            trigger: isNot ? doesNotExist(productCard) : productCard,
            isCheck,
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

export function clickOn(element, { isCheck = false, isNot = false } = {}) {
    const selector = `.btn:contains('${element}')`;
    return [
        {
            content: `Click on '${element}' button`,
            trigger: isNot ? doesNotExist(selector) : selector,
            isCheck,
        },
    ];
}
