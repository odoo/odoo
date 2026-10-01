import { expect } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { clickBtn } from "./common";

export async function isCartPageShown() {
    await waitFor(".o_self_cart_page");
}

export async function clickCheckout() {
    await clickBtn("Checkout");
}

export async function clickOrder() {
    await clickBtn("Order");
}

export async function clickPay() {
    await clickBtn("Pay");
}

export async function clickBackFromCart() {
    await contains(".btn.btn-back").click();
    await animationFrame();
}

// `name` scopes the click to the cart line of that product; without it the
// first matching button of the page is used (fine when the cart has one line).
async function clickCartItemBtn(name, icon) {
    const scope = name ? `.product-cart-item:has(div:contains('${name}'))` : ".btn";
    await contains(`${scope} [data-icon='${icon}']`).click();
    await animationFrame();
}

export async function increaseCartItemQty(name) {
    await clickCartItemBtn(name, "add");
}

export async function decreaseCartItemQty(name) {
    await clickCartItemBtn(name, "remove");
}

export async function removeCartItem(name) {
    await clickCartItemBtn(name, "delete");
}

export async function clickOrderNoteBtn() {
    await contains(".order-note").click();
    await animationFrame();
}

export function checkNoOrderNote() {
    expect(".order-note").toHaveCount(0);
}

export async function clickCancelOrder() {
    await contains('.o_self_cart_page .btn:contains("Cancel")').click();
    await animationFrame();
    await contains(".modal-dialog .btn:contains('Cancel Order')").click();
    await animationFrame();
}

export async function checkProductInCart(name, price, quantity = "1") {
    await waitFor(
        `.product-cart-item:has(div:contains("${name}")):has(div:contains("${quantity}")):has(div .o-so-tabular-nums:contains("${price}"))`
    );
}

export async function checkAttributeInCart(productName, attributes) {
    let selector = `.product-cart-item div:contains("${productName}")`;
    for (const attr of attributes) {
        selector += `:has(div:contains("${attr.name}: ${attr.value}"))`;
    }
    await waitFor(selector);
}

export async function checkComboInCart(comboName, products) {
    for (const product of products) {
        let selector = `.product-cart-item div:contains("${comboName}"):has(div:contains(${product.product}))`;
        if (product.attributes.length > 0) {
            for (const attr of product.attributes) {
                selector += `:has(div:contains("${attr.name}") div:contains("${attr.value}"))`;
            }
        }
        await waitFor(selector);
    }
}

export async function checkTotalPrice(price) {
    await waitFor(`.order-price :contains(Total):contains(${price})`);
}

export async function hasCartItem({ productName, qty, price, attributes, combos }) {
    let selector = `.product-cart-item:has(div:contains(${productName}))`;
    if (qty) {
        selector += `:has(.btn-group .o-so-tabular-nums:contains(${qty}))`;
    }
    if (price) {
        selector += `:has(.line-price:contains(${price}))`;
    }
    for (const attr of attributes || []) {
        selector += `:has(div:contains(${attr}))`;
    }
    for (const comboLine of combos || []) {
        selector += `:has(div:contains(${comboLine}))`;
    }
    await waitFor(selector);
    expect(selector).toBeVisible();
}

export async function cartTotalIs(total) {
    const selector = `.order-price span:contains(${total})`;
    await waitFor(selector);
    expect(selector).toBeVisible();
}

export async function confirmCart(products, total) {
    const cartItemAsserts = products.map((p) => hasCartItem(p));
    if (total !== undefined) {
        cartItemAsserts.push(cartTotalIs(total));
    }
    await Promise.all(cartItemAsserts);
}

export async function checkMissingRequiredsExists() {
    await waitFor("div.missing_required_details");
}

export async function clickMissingRequireds() {
    await contains("div.missing_required_details button").click();
    await animationFrame();
}

export async function selectFirstAddressDropdown() {
    await contains(".o-autocomplete--dropdown-menu .dropdown-item").click();
    await animationFrame();
}

export async function checkAddressError() {
    await waitFor("p.text-danger:contains('Delivery isn\u2019t available')");
}
