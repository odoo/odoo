import { expect } from "@odoo/hoot";
import { animationFrame, waitFor, queryAll } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function selectLocation(name) {
    await contains(`.o_self_eating_location_box .preset_btn:contains('${name}')`).click();
    await animationFrame();
}

export async function clickTakeaway() {
    await contains("button:contains('Takeaway')").click();
    await animationFrame();
}

export async function selectFloor(floor) {
    await contains(
        `.self_order_pills_selection_popup .preset_date_buttons:contains('${floor}')`
    ).click();
    await animationFrame();
}

export async function selectTable(table) {
    await contains(`.self_order_pills_selection_popup .option-item:contains('${table}')`).click();
    await animationFrame();
    await contains(`.self_order_pills_selection_popup .btn-primary:contains('Confirm')`).click();
    await animationFrame();
}

export async function selectTimeSlot() {
    await waitFor(".self_order_pills_selection_popup");
    await contains(".self_order_pills_selection_popup .option-item:first").click();
    await animationFrame();
    await contains(".self_order_pills_selection_popup .btn-primary:contains('Confirm')").click();
    await animationFrame();
}

export async function selectSpecificSlot(slotValue) {
    await waitFor(".self_order_pills_selection_popup");
    await contains(
        `.self_order_pills_selection_popup .option-item:contains('${slotValue}')`
    ).click();
    await animationFrame();
    await contains(".self_order_pills_selection_popup .btn-primary:contains('Confirm')").click();
    await animationFrame();
}

export async function checkSlotUnavailable(slotValue) {
    await waitFor(".self_order_pills_selection_popup");
    const slots = queryAll(".self_order_pills_selection_popup .option-item").map((slot) =>
        slot.textContent.trim()
    );
    if (slots.includes(slotValue)) {
        throw new Error(`${slotValue} should not be available`);
    }
}

export async function checkNoTableSelector() {
    expect(".self_order_popup_table").toHaveCount(0);
}

export async function clickPresetBtn() {
    await contains("button.preset-btn").click();
    await animationFrame();
}

export async function checkPreset(name) {
    await waitFor(`button.preset-btn:contains('${name}')`);
}
