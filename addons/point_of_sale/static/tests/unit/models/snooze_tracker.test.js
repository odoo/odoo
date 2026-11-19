import { expect, freezeTime, mockDate, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";
import { SnoozeTracker } from "@point_of_sale/app/models/utils/snooze_tracker";
import { definePosModels } from "../data/generate_model_definitions";
import { setupPosEnv } from "../utils";

const { DateTime } = luxon;

definePosModels();

test("snooze countdown, expiry and variant lookup", async () => {
    const store = await setupPosEnv();
    mockDate("2026-01-01 12:00:00");
    freezeTime();
    const variant = store.models["product.product"].get(52);
    const template = variant.product_tmpl_id;
    const snooze = store.models["pos.snooze"].create({
        product_template_id: template,
        start_time: DateTime.now(),
        end_time: DateTime.now().plus({ seconds: 2 }),
    });
    const tracker = new SnoozeTracker([snooze]);

    expect(tracker.isProductSnoozed(template)).toBe(true);
    expect(tracker.isProductSnoozed(variant)).toBe(true);
    expect(tracker.getActiveSnooze("product", { product: variant })).toBe(snooze);
    expect(String(tracker.getProductSnoozeLabel(variant))).toBe("Snoozed - 00:00:02 left");
    await advanceTime(1000);
    expect(String(tracker.getProductSnoozeLabel(variant))).toBe("Snoozed - 00:00:01 left");
    await advanceTime(2000);
    expect(tracker.state.now).toBe(0);
    expect(tracker.getSnoozeCountdown(snooze)).toEqual(["", undefined]);
    expect(tracker.getProductSnoozeLabel(variant)).toBe("");

    snooze.end_time = null;
    tracker.setSnoozes([snooze]);
    expect(String(tracker.getProductSnoozeLabel(variant))).toBe("Snoozed - session");
    const [countdown, activeSnooze] = tracker.getSnoozeCountdown(snooze);
    expect(String(countdown)).toBe("Next session");
    expect(activeSnooze).toBe(snooze);
});
