import { animationFrame, queryAll } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

export async function increaseTicketQty(ticketName, times = 1) {
    for (let i = 0; i < times; i++) {
        const row = queryAll(".modal .o_event_configurator_popup > div").find((el) =>
            el.textContent.includes(ticketName)
        );
        await contains(row.querySelector('[data-icon="add"]')).click();
        await animationFrame();
    }
}

export function ticketAvailabilityText(ticketName) {
    const row = queryAll(".modal .o_event_configurator_popup > div").find((el) =>
        el.textContent.includes(ticketName)
    );
    return row ? row.textContent.replace(/\s+/g, " ").trim() : "";
}

export async function confirmEventPopup() {
    await contains(".modal:not(.o_inactive_modal) .modal-footer .btn-primary").click();
    await animationFrame();
}

export function slotButton(time) {
    return queryAll(".modal .o_event_slot_btn").find((el) => el.textContent.includes(time));
}

export async function selectSlot(time) {
    await contains(slotButton(time)).click();
    await animationFrame();
}
