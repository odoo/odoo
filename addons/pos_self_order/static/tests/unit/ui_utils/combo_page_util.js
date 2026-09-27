import { animationFrame, waitFor, queryFirst } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { clickBtn } from "./common";
import { setupAttribute, setupAttributeNew } from "./product_page_util";

export async function clickComboProduct(productName) {
    await contains(`.combo_product_box span:contains('${productName}')`).click();
    await animationFrame();
}

export async function setupCombo(products) {
    for (const product of products) {
        await clickComboProduct(product.product);
        if (product.attributes.length > 0) {
            await setupAttribute(product.attributes);
            await clickBtn("Next");
        }
    }
}

export async function setupComboNew(products) {
    for (const { product, qty, attributes } of products) {
        await contains(`.o_self_product_card span:contains('${product}')`).click();
        await animationFrame();
        if (qty && qty > 1) {
            for (let i = 1; i < qty; i++) {
                await contains(`.o_self_product_card span:contains('${product}')`).click();
                await animationFrame();
            }
        }
        if (attributes?.length > 0) {
            await setupAttributeNew(attributes, false);
        }
        await contains(".btn:contains('Next')").click();
        await animationFrame();
    }
    await contains(".btn:contains('Add to cart')").click();
    await animationFrame();
}

export async function clickNext() {
    await clickBtn("Next");
}

export async function increaseComboItemQty(productName, qty) {
    await waitFor(`.combo_product_box span:contains("${productName}")`);
    for (let i = 1; i < qty; i++) {
        await waitFor(`.item_qty_container .o-so-tabular-nums:contains("${i}")`);
        await contains(".item_qty_container button:eq(1)").click();
        await animationFrame();
    }
}

export async function verifyItemHasPriceBadge(productName, price) {
    await waitFor(
        `.combo_product_box:has(span:contains('${productName}')) .badge:contains('+ $ ${price}')`
    );
}

export async function verifyItemHasExtraBadge(productName, price) {
    await waitFor(
        `.combo_product_box:has(span:contains('${productName}')) .badge:contains('Extra: $ ${price}')`
    );
}

export async function verifyItemHasNoExtraBadge(productName) {
    const box = queryFirst(`.combo_product_box:has(span:contains('${productName}'))`);
    if (box) {
        const badge = box.querySelector(".badge");
        if (badge && badge.textContent.includes("Extra")) {
            throw new Error(`Product '${productName}' should not have Extra badge`);
        }
    }
}

export async function verifyConfirmationPageShown() {
    await waitFor(".o_self_combo_confirmation:contains('Validate your selection')");
}

export async function verifyConfirmationHasExtraPrice(productName) {
    await waitFor(".o_self_combo_confirmation .badge:contains('Extra:')");
}
