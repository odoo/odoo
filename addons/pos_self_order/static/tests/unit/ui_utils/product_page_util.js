import { expect } from "@odoo/hoot";
import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { clickBtn, isMobile } from "./common";

export async function setupAttribute(attributes) {
    for (const attr of attributes) {
        await contains(
            `h2:contains("${attr.name}") + div.row button:contains("${attr.value}")`
        ).click();
        await animationFrame();
    }
}

export async function setupAttributeNew(attributes, clickAddToCart = true) {
    for (const { name, value } of attributes) {
        await contains(
            `.o_self_product_page_attributes h2:contains("${name}") + div.row button:contains("${value}")`
        ).click();
        await animationFrame();
    }
    if (clickAddToCart) {
        await contains(".btn:contains('Add to cart')").click();
        await animationFrame();
    }
}

export async function selectAttributeValue(value) {
    await contains(`.self_order_attribute_selection button:contains('${value}')`).click();
    await animationFrame();
}

export async function selectNthAttributeValue(n, attributeName) {
    const scope = attributeName ? `h2:contains(${attributeName}) + ` : "";
    await contains(`${scope}.self_order_attribute_selection div:nth-child(${n}) button`).click();
    await animationFrame();
}

export function checkAttributeShown(name) {
    expect(`div h2:contains('${name}')`).toHaveCount(1);
}

export function checkAttributeIsOptional(name) {
    expect(`h2:contains('${name}') .badge`).toHaveCount(0);
}

export function checkAttributeValueCount(count) {
    expect(".self_order_attribute_selection button").toHaveCount(count);
}

export function checkAttributeGroups(groupCount, valuePerGroup) {
    expect(`.self_order_attribute_selection:has(button:count(${valuePerGroup}))`).toHaveCount(
        groupCount
    );
}

export function checkAttributeGroupHasValues(values) {
    let selector = ".self_order_attribute_selection";
    for (const value of values) {
        selector += `:has(button:contains('${value}'))`;
    }
    expect(selector).toHaveCount(1);
}

export async function attributeHasColorDot(attribute) {
    await waitFor(`div:has(span:contains("${attribute}")) ~ div.rounded-5`);
}

export async function attributeHasImage(attribute) {
    await waitFor(`div:has(span:contains("${attribute}")) ~ img.rounded-4`);
}

export async function clickAddToCart() {
    await clickBtn("Add to cart");
}

export async function clickDiscard() {
    await contains(".btn.btn-link [data-icon='close_small']").click();
    await animationFrame();
}

export async function clickBackFromProduct() {
    if (isMobile()) {
        await contains("[data-icon='chevron_backward']").click();
        await animationFrame();
    } else {
        await clickBtn("Back");
    }
}
