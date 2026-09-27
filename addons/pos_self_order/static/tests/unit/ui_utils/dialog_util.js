import { animationFrame, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { clickBtn } from "./common";

export async function confirmDialog(buttonText) {
    await waitFor(".modal");
    if (buttonText) {
        await contains(`.modal .btn:contains("${buttonText}")`).click();
    } else {
        await contains(".modal .btn-primary").click();
    }
    await animationFrame();
}

export async function cancelDialog() {
    await waitFor(".modal");
    await contains(".modal .btn-secondary").click();
    await animationFrame();
}

export async function dialogBodyIs(text) {
    await waitFor(`.modal-body:contains("${text}")`);
}

export async function clickCancelPopup() {
    await contains(".btn.btn-cancel").click();
    await animationFrame();
}

export async function clickTextArea() {
    await contains(".modal:not(.o_inactive_modal) textarea").click();
    await animationFrame();
}

export async function typeNote(text) {
    await contains(".modal:not(.o_inactive_modal) textarea").edit(text);
    await animationFrame();
}

export async function clickApply() {
    await clickBtn("Apply");
}

export async function clickOk() {
    await clickBtn("Ok");
}

export async function clickClose() {
    await clickBtn("Close");
}

export async function clickContinue() {
    await clickBtn("Continue");
}
