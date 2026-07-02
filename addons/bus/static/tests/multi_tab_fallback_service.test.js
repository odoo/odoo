import { describe, expect, test } from "@odoo/hoot";
import { multiTabFallbackService } from "@bus/multi_tab_fallback_service";
import { getService, makeTestApp, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

registry.category("services").remove("multi_tab");
registry.category("services").add("multi_tab", multiTabFallbackService);
describe.current.tags("desktop");

test("main tab service(local storage) elects new main on pagehide", async () => {
    await makeTestApp({ forceNew: true });
    const multiTab1 = getService("multi_tab");
    expect(await multiTab1.isOnMainTab()).toBe(true);
    // Prevent second tab from receiving pagehide event.
    patchWithCleanup(browser, {
        addEventListener(eventName, callback) {
            if (eventName != "pagehide") {
                super.addEventListener(eventName, callback);
            }
        },
    });
    await makeTestApp({ forceNew: true });
    const multiTab2 = getService("multi_tab");
    expect(await multiTab2.isOnMainTab()).toBe(false);
    multiTab1.bus.addEventListener("no_longer_main_tab", () =>
        expect.step("tab1 no_longer_main_tab")
    );
    multiTab2.bus.addEventListener("no_longer_main_tab", () =>
        expect.step("tab2 no_longer_main_tab")
    );
    multiTab2.bus.addEventListener("become_main_tab", () => expect.step("tab2 become_main_tab"));
    browser.dispatchEvent(new Event("pagehide"));

    await expect.waitForSteps(["tab1 no_longer_main_tab", "tab2 become_main_tab"]);
    expect(await multiTab1.isOnMainTab()).toBe(false);
    expect(await multiTab2.isOnMainTab()).toBe(true);
});
