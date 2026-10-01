import { animationFrame, queryAll } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { ensurePane, longPress } from "./common";

export async function clickOrderline(productName) {
    await ensurePane("left");
    await contains(`.orderline .product-name:contains("${productName}")`).click();
    await animationFrame();
}

export async function longPressOrderline(productName) {
    await ensurePane("left");
    await longPress(productName, ".order-container .orderline");
}

export function getOrderTotal() {
    const el = document.querySelector(".order-summary .total");
    return el ? el.textContent.trim() : "";
}

export function getOrderTax() {
    const el = document.querySelector("#order-widget-taxes .tax");
    return el ? el.textContent.trim() : "";
}

export function getOrderlineNames() {
    return queryAll(".orderline .product-name").map((el) => el.textContent.trim());
}

export function hasOrderline({
    withClass = "",
    withoutClass = "",
    productName,
    quantity,
    price,
    priceUnit,
    customerNote,
    internalNote,
    comboParent,
    discount,
    oldPrice,
    priceNoDiscount,
    attributeLine,
    refundQty,
} = {}) {
    const orderlines = queryAll(`.order-container .orderline${withClass}`);
    return orderlines.some((el) => {
        if (withoutClass && el.matches(withoutClass)) {
            return false;
        }
        if (productName) {
            const nameEl = el.querySelector(".product-name");
            if (!nameEl || !nameEl.textContent.includes(productName)) {
                return false;
            }
        }
        const formatQty = (value) =>
            parseFloat(value) % 1 === 0 ? parseInt(value, 10).toString() : value;
        if (quantity) {
            const qtyEl = el.querySelector(".qty");
            if (!qtyEl || !qtyEl.textContent.includes(formatQty(quantity))) {
                return false;
            }
        }
        if (refundQty) {
            const refundEl = el.querySelector(".qty .refund");
            if (!refundEl || !refundEl.textContent.includes(formatQty(refundQty))) {
                return false;
            }
        }
        if (price) {
            const priceEl = el.querySelector(".price");
            if (!priceEl || !priceEl.textContent.includes(price)) {
                return false;
            }
        }
        if (priceUnit) {
            const puEl = el.querySelector(".price-per-unit");
            if (!puEl || !puEl.textContent.includes(priceUnit)) {
                return false;
            }
        }
        if (customerNote) {
            const noteEl = el.querySelector(".info-list .customer-note");
            if (!noteEl || !noteEl.textContent.includes(customerNote)) {
                return false;
            }
        }
        if (internalNote) {
            const noteEl = el.querySelector(".info-list .o_tag_badge_text");
            if (!noteEl || !noteEl.textContent.includes(internalNote)) {
                return false;
            }
        }
        if (comboParent) {
            const cpEl = el.querySelector(".info-list .combo-parent-name");
            if (!cpEl || !cpEl.textContent.includes(comboParent)) {
                return false;
            }
        }
        if (discount || discount === "") {
            const discEl = el.querySelector(".info-list .discount.em");
            if (!discEl || !discEl.textContent.includes(discount)) {
                return false;
            }
        }
        if (priceNoDiscount) {
            const infoEl = el.querySelector(".info-list");
            if (!infoEl || !infoEl.textContent.includes(priceNoDiscount)) {
                return false;
            }
        }
        if (attributeLine) {
            const attrEl = el.querySelector(".attribute-line");
            if (!attrEl || !attrEl.textContent.includes(attributeLine)) {
                return false;
            }
        }
        return true;
    });
}

export function doesNotHaveOrderline(options = {}) {
    return !hasOrderline(options);
}
