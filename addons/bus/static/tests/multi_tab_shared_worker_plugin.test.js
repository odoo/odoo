import { describe, expect, test, afterEach, beforeEach } from "@odoo/hoot";
import { MultiTabSharedWorkerPlugin } from "@bus/multi_tab_shared_worker_plugin";
import { WorkerPlugin } from "@bus/services/worker_plugin";
import { getService, makeTestApp, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { services } from "@web/core/services";

describe.current.tags("desktop");

beforeEach(() => {
    services.add(MultiTabSharedWorkerPlugin);
});
afterEach(() => {
    services.delete(MultiTabSharedWorkerPlugin);
});

test("main tab service(election worker) elects new main on pagehide", async () => {
    await makeTestApp({ forceNew: true });
    const multiTab1 = getService(MultiTabSharedWorkerPlugin);
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
    const multiTab2 = getService(MultiTabSharedWorkerPlugin);
    expect(await multiTab2.isOnMainTab()).toBe(false);
    multiTab1.bus.addEventListener("become_main_tab", () => expect.step("tab1 become_main_tab"));
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

test("main tab service(election worker) elects new main after unregister main tab", async () => {
    await makeTestApp({ forceNew: true });
    const multiTab1 = getService(MultiTabSharedWorkerPlugin);
    expect(await multiTab1.isOnMainTab()).toBe(true);
    await makeTestApp({ forceNew: true });
    const multiTab2 = getService(MultiTabSharedWorkerPlugin);
    expect(await multiTab2.isOnMainTab()).toBe(false);
    multiTab1.bus.addEventListener("become_main_tab", () => expect.step("tab1 become_main_tab"));
    multiTab1.bus.addEventListener("no_longer_main_tab", () =>
        expect.step("tab1 no_longer_main_tab")
    );
    multiTab2.bus.addEventListener("no_longer_main_tab", () =>
        expect.step("tab2 no_longer_main_tab")
    );
    multiTab2.bus.addEventListener("become_main_tab", () => expect.step("tab2 become_main_tab"));
    multiTab1.unregister();

    await expect.waitForSteps(["tab1 no_longer_main_tab", "tab2 become_main_tab"]);
    expect(await multiTab1.isOnMainTab()).toBe(false);
    expect(await multiTab2.isOnMainTab()).toBe(true);
});

test("main tab is elected again in the new worker after a worker upgrade", async () => {
    await makeTestApp();
    const multiTab = getService(MultiTabSharedWorkerPlugin);
    expect(await multiTab.isOnMainTab()).toBe(true);
    multiTab.bus.addEventListener("no_longer_main_tab", () => expect.step("no_longer_main_tab"));
    multiTab.bus.addEventListener("become_main_tab", () => expect.step("become_main_tab"));
    await getService(WorkerPlugin).upgrade("test.1", "BUS:LEAVE", "BUS:LEAVE_RESPONSE");
    await expect.waitForSteps(["no_longer_main_tab", "become_main_tab"]);
    expect(await multiTab.isOnMainTab()).toBe(true);
});
