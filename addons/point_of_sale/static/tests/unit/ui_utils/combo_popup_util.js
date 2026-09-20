import { animationFrame } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function selectComboItem(productName) {
    await contains(
        `.modal label.combo-item article.product:has(.product-name:contains("${productName}"))`
    ).click();
    await animationFrame();
}

export async function confirmCombo() {
    await contains(".modal footer button.confirm").click();
    await animationFrame();
}

export async function selectComboItems(items) {
    for (const item of items) {
        await selectComboItem(item);
    }
}

export async function configureAndConfirmCombo(selections) {
    for (const selection of selections) {
        await selectComboItem(selection);
    }
    await confirmCombo();
}

export function isComboItemSelected(productName) {
    const el = [
        ...document.querySelectorAll(".modal label.combo-item.selected .product-name"),
    ].find((el) => el.textContent.includes(productName));
    return el !== null;
}
