import { animationFrame, press } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { normalizeText } from "./common";

export function numberPopupValue() {
    const el = document.querySelector(".modal .popup-input .input-value");
    return el ? normalizeText(el.textContent) : null;
}

export async function clickNumberPopupType(name) {
    await contains(`.modal .number-popup-types .number-popup-type-${name}`).click();
    await animationFrame();
}

export function selectedNumberPopupType() {
    const el = document.querySelector(".modal .number-popup-types .number-popup-type.text-primary");
    const type = el && [...el.classList].find((cls) => cls.startsWith("number-popup-type-"));
    return type ? type.slice("number-popup-type-".length) : null;
}

export async function confirmNumberPopup() {
    await press("Enter");
    await animationFrame();
}
