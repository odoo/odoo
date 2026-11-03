import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { normalizeText, isMobile } from "./common";

export async function confirmDialog(buttonText) {
    await waitFor(".modal");
    if (buttonText) {
        await contains(`.modal .btn:contains("${buttonText}")`).click();
    } else {
        await contains(".modal .btn-primary").click();
    }
    await animationFrame();
}

export async function cancelDialog(btnLabel = "Discard", title = "") {
    await waitFor(".modal");
    if (title) {
        await contains(
            `.modal:has(.modal-title:contains(${title})) .btn-secondary:contains(${btnLabel})`
        ).click();
    } else {
        await contains(`.modal .btn-secondary:contains(${btnLabel})`).click();
    }
    await animationFrame();
}

export async function closeDialog() {
    await waitFor(".modal");
    if (isMobile()) {
        await contains(".modal-header button[data-icon='arrow_back']").click();
    } else {
        await contains(`.modal button.btn-close`).click();
    }
    await animationFrame();
}

export async function closePrintingError() {
    await waitFor(".modal");
    await contains(".modal .btn-primary").click();
    await animationFrame();
}

export function dialogTitle() {
    const el = document.querySelector(".modal .modal-title");
    return el ? normalizeText(el.textContent) : null;
}

export async function dialogBody() {
    await waitFor(".modal .modal-body");
    return normalizeText(document.querySelector(".modal .modal-body").textContent);
}
