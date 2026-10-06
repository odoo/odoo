import { expect } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function isProductListPageShown() {
    await waitFor(".o_self_product_list_page");
}

export async function clickProduct(name) {
    await contains(`.o_self_product_card span:contains('${name}')`).click();
    await animationFrame();
}

export async function clickProductCard(productName) {
    await contains(`.o_self_product_card span:contains('${productName}')`).click();
    await animationFrame();
}

export async function clickProductInfo(name) {
    await contains(`.o_self_product_card:contains('${name}') .product_info_icon`).click();
    await animationFrame();
}

export async function clickCategory(name) {
    await contains(`.category_btn:contains('${name}')`).click();
    await animationFrame();
}

export async function checkCategoryBtn(name) {
    await waitFor(`.category_btn:contains('${name}')`);
}

export function checkIsNoCategoryBtn(name) {
    expect(`.category_btn:contains('${name}')`).toHaveCount(0);
}

export async function clickChildCategory(name) {
    await contains(`.child_category_btn:contains('${name}')`).click();
    await animationFrame();
}

export async function waitProduct(name) {
    await waitFor(`.o_self_product_card span:contains('${name}')`);
}

export async function checkProductQty(name, qty) {
    await waitFor(
        `.o_self_product_list_page .o_self_product_card:has(.self_order_product_name:contains('${name}')) .badge:contains('${qty}')`
    );
}

export function expectProductCardQty(productName, qty) {
    expect(
        `.o_self_product_card:has(.self_order_product_name:contains(${productName})):has(.badge:contains(${qty}))`
    ).toBeVisible();
}

export async function checkOrderTotal(amount) {
    await waitFor(
        `.o_self_product_list_page .o_self_shadow_bottom .o-so-tabular-nums:contains('${amount}')`
    );
}

export async function checkReferenceNotInProductName(productName, reference) {
    await waitFor(
        `.o_self_product_card span:contains('${productName}'):not(:contains("${reference}"))`
    );
}

export function isProductDisplayed(productName, isOutOfStock = false) {
    let selector = `.o_self_product_card:has(span:contains('${productName}'))`;
    if (isOutOfStock) {
        selector += `:has(div:contains('Out of stock'))`;
    }
    return waitFor(selector);
}

export async function isProductNotDisplayed(productName) {
    expect(`.o_self_product_card:has(span:contains('${productName}'))`).toHaveCount(0);
}

export function checkNthProduct(n, name) {
    expect(
        `.product_list .o_self_product_card:nth-child(${n}) span:contains('${name}')`
    ).toHaveCount(1);
}

export async function setProductAvailability(store, productName, value) {
    const product = store.models["product.product"].find((p) => p.name === productName);
    const productTmpl = store.models["product.template"].find((p) => p.name === productName);
    if (!product) {
        throw new Error(`Product '${productName}' not found.`);
    }
    product.self_order_available = value;
    productTmpl.self_order_available = value;
    await animationFrame();
}

export async function clickCancelFromProductList() {
    await contains(".btn.btn-cancel").click();
    await animationFrame();
    await contains(".btn.btn-primary:contains('Cancel Order')").click();
    await animationFrame();
}
