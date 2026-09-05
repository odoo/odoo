import { animationFrame, queryAll, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";
import { ensurePane, isMobile } from "@point_of_sale/../tests/unit/ui_utils";

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

export async function clickPricelist(name) {
    await ensurePane("left");
    let button = document.querySelector(".o_pricelist_button");
    if (!button) {
        await contains(
            isMobile() ? ".product-screen .mobile-more-button" : ".product-screen .more-btn"
        ).click();
        await animationFrame();
        button = document.querySelector(".o_pricelist_button");
    }
    await contains(button).click();
    await animationFrame();
    await waitFor(".selection-item");
    await contains(`.selection-item:contains("${name}")`).click();
    await animationFrame();
}

export function createFixedPricelist(store, { id, name, productId, price }) {
    const pricelist = store.models["product.pricelist"].create({
        id,
        name,
        display_name: `${name} (USD)`,
        item_ids: [],
    });
    const item = store.models["product.pricelist.item"].create({
        id,
        pricelist_id: pricelist.id,
        product_id: store.models["product.product"].get(productId),
        compute_price: "fixed",
        fixed_price: price,
        base: "list_price",
        min_quantity: 0,
    });
    pricelist.item_ids = [item];
    pricelist.computeRuleIndexes();
    return pricelist;
}
