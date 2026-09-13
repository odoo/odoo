// @ts-check

import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, freezeTime } from "@odoo/hoot-mock";
import { getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { makeLogger } from "@web/core/debug/debug_logger";
import { MainComponentsContainer } from "@web/ui/main_components_container";

beforeEach(async () => {
    await mountWithCleanup(MainComponentsContainer);
});

/** @returns {string} */
function message() {
    return document.querySelector(".o_blockUI .o_message")?.textContent?.trim() ?? "";
}

test("block() shows the overlay and its first message at once", async () => {
    expect(".o_blockUI").toHaveCount(0);
    getService("ui").block();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(1);
    expect(".o_blockUI").not.toHaveClass("o_blockUI_invisible");
    expect(".o_blockUI .o_spinner").toHaveCount(1);
    expect(message()).toBe("Loading...");

    getService("ui").unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);
});

test("a delayed block is present but invisible until the delay elapses", async () => {
    getService("ui").block({ delay: 500 });
    await animationFrame();
    expect(".o_blockUI").toHaveCount(1);
    expect(".o_blockUI").toHaveClass("o_blockUI_invisible");
    expect(".o_blockUI .o_spinner").toHaveCount(0);
    expect(".o_blockUI .o_message").toHaveCount(0);

    await advanceTime(400);
    expect(".o_blockUI").toHaveClass("o_blockUI_invisible");

    await advanceTime(100);
    await animationFrame();
    expect(".o_blockUI").not.toHaveClass("o_blockUI_invisible");
    expect(message()).toBe("Loading...");
});

test("unblocking before the delay never shows the overlay", async () => {
    getService("ui").block({ delay: 500 });
    await animationFrame();
    getService("ui").unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);

    await advanceTime(1000);
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);
});

test("a caller's own message replaces the escalating ladder", async () => {
    getService("ui").block({ message: "Exporting 4 records" });
    await animationFrame();
    expect(message()).toBe("Exporting 4 records");

    await advanceTime(3600 * 1000);
    await animationFrame();
    expect(message()).toBe("Exporting 4 records");
});

test("the message ladder escalates at its stated onsets", async () => {
    freezeTime();
    const started = Date.now();
    const log = makeLogger("web.ui.block_test");
    const advanceTo = async (milliseconds) => {
        await advanceTime(started + milliseconds - Date.now());
        await animationFrame();
        log.logic("boundary", () => ({
            elapsed: Date.now() - started,
            message: message(),
        }));
    };
    getService("ui").block();
    await advanceTo(0);
    expect(message()).toBe("Loading...");

    /** @type {[number, string][]} */
    const ladder = [
        [20, "Still loading..."],
        [60, "Still loading...Please be patient."],
        [120, "Don't leave yet,it's still loading..."],
        [240, "You may not believe it,but the application is actually loading..."],
        [420, "Take a minute to get a coffee,because it's loading..."],
        [3600, "Maybe you should consider reloading the application by pressing F5..."],
    ];
    for (const [onset, expected] of ladder) {
        await advanceTo(onset * 1000 - 500);
        expect(message()).not.toBe(expected);

        await advanceTo(onset * 1000);
        expect(message()).toBe(expected);
    }

    await advanceTo(7200 * 1000);
    expect(message()).toBe(/** @type {any[]} */ (ladder.at(-1))[1]);
});

test("unblock cancels the ladder rather than letting it run on", async () => {
    getService("ui").block();
    await animationFrame();
    await advanceTime(20_000);
    await animationFrame();
    expect(message()).toBe("Still loading...");

    getService("ui").unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);

    await advanceTime(3600 * 1000);
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);

    getService("ui").block();
    await animationFrame();
    expect(message()).toBe("Loading...");
});

test("nested blocks show one overlay and need as many unblocks", async () => {
    const ui = getService("ui");
    ui.block();
    ui.block();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(1);

    ui.unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(1);

    ui.unblock();
    await animationFrame();
    expect(".o_blockUI").toHaveCount(0);
});
