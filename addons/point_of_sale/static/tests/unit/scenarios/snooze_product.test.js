import { test, expect } from "@odoo/hoot";
import { waitFor } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { definePosModels } from "../data/generate_model_definitions";
import { SnoozedProductTracker } from "@point_of_sale/app/models/utils/snooze_tracker";
import { setupPosEnv } from "../utils";
import { ProductInfoPopup } from "@point_of_sale/app/components/popups/product_info_popup/product_info_popup";
import { serializeDateTime } from "@web/core/l10n/dates";

const { DateTime } = luxon;
definePosModels();

test("test_pos_snooze: snooze tracker marks product as unavailable then available", async () => {
    const now = DateTime.now();
    const product = { id: 42 };
    const tracker = new SnoozedProductTracker([
        {
            raw: { product_template_id: 42 },
            product_template_id: product,
            start_time: now.minus({ minutes: 5 }),
            end_time: now.plus({ minutes: 55 }),
        },
    ]);

    expect(tracker.isProductSnoozed(product)).toBe(true);

    tracker.setSnoozes([]);
    expect(tracker.isProductSnoozed(product)).toBe(false);
    expect(tracker.getActiveSnooze(product)).toBe(null);
});

test("test_pos_snooze: ProductInfoPopup displays warning button state for snoozed product", async () => {
    const store = await setupPosEnv();
    const now = DateTime.now();
    const endTime = now.plus({ hours: 1 });

    const product = store.models["product.template"].get(5);
    const snooze = store.models["pos.product.template.snooze"].create({
        id: 2,
        product_template_id: product,
        pos_config_id: store.config,
        start_time: serializeDateTime(now),
        end_time: serializeDateTime(endTime),
    });

    store.snoozedProductTracker.setSnoozes([snooze]);
    store.addNewOrder();
    const info = await store.getProductInfo(product);
    await mountWithCleanup(ProductInfoPopup, {
        props: {
            productTemplate: product,
            info: info,
            close: () => {},
        },
    });

    const snoozeButton = document.querySelector(".section-inventory .btn");
    expect(snoozeButton.classList.contains("btn-warning")).toBe(true);
    expect(snoozeButton.classList.contains("btn-secondary")).toBe(false);
});

test("test_pos_snooze: ProductInfoPopup displays available button state for non-snoozed product", async () => {
    const store = await setupPosEnv();

    const product = store.models["product.template"].get(5);
    store.snoozedProductTracker.setSnoozes([]);
    store.addNewOrder();
    const info = await store.getProductInfo(product);
    await mountWithCleanup(ProductInfoPopup, {
        props: {
            productTemplate: product,
            info: info,
            close: () => {},
        },
    });

    const snoozeButton = document.querySelector(".section-inventory .btn");
    expect(snoozeButton.classList.contains("btn-secondary")).toBe(true);
    expect(snoozeButton.classList.contains("btn-warning")).toBe(false);
});

test("test_pos_snooze: stop snooze confirmation dialog displays warning message", async () => {
    const store = await setupPosEnv();
    const now = DateTime.now();
    const endTime = now.plus({ hours: 1 });

    const product = store.models["product.template"].get(5);
    const snooze = store.models["pos.product.template.snooze"].create({
        id: 3,
        product_template_id: product,
        pos_config_id: store.config,
        start_time: serializeDateTime(now),
        end_time: serializeDateTime(endTime),
    });
    store.snoozedProductTracker.setSnoozes([snooze]);
    store.addNewOrder();
    const info = await store.getProductInfo(product);
    await mountWithCleanup(ProductInfoPopup, {
        props: {
            productTemplate: product,
            info: info,
            close: () => {},
        },
    });

    const snoozeButton = document.querySelector(".section-inventory .btn");
    snoozeButton.click();
    await waitFor(".modal .modal-title:contains('Stop Snooze')");
    const dialog = [...document.querySelectorAll(".modal .modal-dialog")].find((el) =>
        el.textContent.includes("Stop Snooze")
    );
    expect(dialog.textContent.includes("Do you want to stop the snooze early")).toBe(true);
    expect(dialog.textContent.includes("make the product available again immediately")).toBe(true);
});
