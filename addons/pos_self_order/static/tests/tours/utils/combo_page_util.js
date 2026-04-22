/**
 * Verify that a combo item shows a price badge (for qty_free=0)
 * Badge format: "+ €X" (not "Extra:")
 */
export function verifyItemHasPriceBadge(productName, price) {
    return {
        content: `Verify '${productName}' shows price badge with price ${price}`,
        trigger: `.combo_product_box:has(span:contains('${productName}')) .badge:contains('+ $ ${price}')`,
    };
}

/**
 * Verify that a combo item shows an "Extra:" badge (for qty > qty_free)
 */
export function verifyItemHasExtraBadge(productName, price) {
    return {
        content: `Verify '${productName}' shows Extra badge with price ${price}`,
        trigger: `.combo_product_box:has(span:contains('${productName}')) .badge:contains('Extra: $ ${price}')`,
    };
}

/**
 * Verify that a combo item does NOT show an extra badge (free item)
 */
export function verifyItemHasNoExtraBadge(productName) {
    return {
        content: `Verify '${productName}' does NOT show Extra badge`,
        trigger: `.combo_product_box:has(span:contains('${productName}'))`,
    };
}

/**
 * Verify confirmation page is displayed
 */
export function verifyConfirmationPageShown() {
    return {
        content: "Verify confirmation page is shown",
        trigger: `.o_self_combo_confirmation:contains('Validate your selection')`,
    };
}

/**
 * Verify extra price appears in confirmation for a specific item
 */
export function verifyConfirmationHasExtraPrice(productName) {
    return {
        content: `Verify confirmation shows extra price for '${productName}'`,
        trigger: `.o_self_combo_confirmation .badge:contains('Extra:')`,
    };
}
