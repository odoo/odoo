import { describe, expect, test } from "@odoo/hoot";
import { makeMockEnv, patchWithCleanup, restoreRegistry } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";

describe.current.tags("desktop");

test("multi tab service elects new main on pagehide", async () => {
    const firstTabEnv = await makeMockEnv();
    expect(await firstTabEnv.services.multi_tab.isOnMainTab()).toBe(true);
    // Prevent second tab from receiving pagehide event.
    patchWithCleanup(browser, {
        addEventListener(eventName, callback) {
            if (eventName != "pagehide") {
                super.addEventListener(eventName, callback);
            }
        },
    });
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    expect(await secondTabEnv.services.multi_tab.isOnMainTab()).toBe(false);
    firstTabEnv.services.multi_tab.bus.addEventListener("no_longer_main_tab", () =>
        expect.step("tab1 no_longer_main_tab")
    );
    secondTabEnv.services.multi_tab.bus.addEventListener("no_longer_main_tab", () =>
        expect.step("tab2 no_longer_main_tab")
    );
    secondTabEnv.services.multi_tab.bus.addEventListener("become_main_tab", () =>
        expect.step("tab2 become_main_tab")
    );
    browser.dispatchEvent(new Event("pagehide"));

    await expect.waitForSteps(["tab1 no_longer_main_tab", "tab2 become_main_tab"]);
    expect(await firstTabEnv.services.multi_tab.isOnMainTab()).toBe(false);
    expect(await secondTabEnv.services.multi_tab.isOnMainTab()).toBe(true);
});

test("multi tab allow to share values between tabs", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    firstTabEnv.services.multi_tab.setSharedValue("foo", 1);
    expect(secondTabEnv.services.multi_tab.getSharedValue("foo")).toBe(1);
    firstTabEnv.services.multi_tab.setSharedValue("foo", 2);
    expect(secondTabEnv.services.multi_tab.getSharedValue("foo")).toBe(2);
    firstTabEnv.services.multi_tab.removeSharedValue("foo");
    expect(secondTabEnv.services.multi_tab.getSharedValue("foo")).toBe(undefined);
});

test("multi tab triggers shared_value_updated", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    secondTabEnv.services.multi_tab.bus.addEventListener("shared_value_updated", ({ detail }) => {
        expect.step(`${detail.key} - ${JSON.parse(detail.newValue)}`);
    });
    firstTabEnv.services.multi_tab.setSharedValue("foo", "bar");
    firstTabEnv.services.multi_tab.setSharedValue("foo", "foo");
    firstTabEnv.services.multi_tab.removeSharedValue("foo");
    await expect.waitForSteps(["foo - bar", "foo - foo", "foo - null"]);
});
