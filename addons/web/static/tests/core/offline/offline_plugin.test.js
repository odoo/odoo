import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";

import { OfflinePlugin } from "@web/core/offline/offline_plugin";

import { advanceTime, animationFrame, expect, test, tick } from "@odoo/hoot";
import { getService, makeTestApp, onRpc, patchWithCleanup } from "@web/../tests/web_test_helpers";

test("RPC:RESPONSE: rpc returning a status 502", async () => {
    expect.errors(1);

    onRpc("/rpc/offline", () => new Response("", { status: 502 }), { pure: true });

    await makeTestApp();
    expect(getService(OfflinePlugin).isOffline()).toBe(false);

    rpc("/rpc/offline");
    await animationFrame();
    expect(getService(OfflinePlugin).isOffline()).toBe(true);

    expect.verifyErrors([
        `Error: Connection to "/rpc/offline" couldn't be established or was interrupted`,
    ]);
});

test("RPC:RESPONSE: any succesfull rpc turns offline off", async () => {
    onRpc("/rpc/thatworks", () => true);

    await makeTestApp();
    getService(OfflinePlugin).setOffline(true);
    await tick();
    expect(getService(OfflinePlugin).isOffline()).toBe(true);

    await rpc("/rpc/thatworks");
    expect(getService(OfflinePlugin).isOffline()).toBe(false);
});

test("'offline' and 'online' events fired on window", async () => {
    let offline = false;
    onRpc(
        "/web/webclient/version_info",
        () => {
            expect.step("version_info");
            if (offline) {
                return new Response("", { status: 502 });
            }
            return new Response("true", { status: 200 });
        },
        { pure: true }
    );

    await makeTestApp();

    offline = true;
    browser.dispatchEvent(new Event("offline"));
    await tick();
    expect.verifySteps(["version_info"]);
    expect(getService(OfflinePlugin).isOffline()).toBe(true);

    offline = false;
    browser.dispatchEvent(new Event("online"));
    await tick();
    expect.verifySteps(["version_info"]);
    expect(getService(OfflinePlugin).isOffline()).toBe(false);
});

test("'offline' and 'online' events fired on window (false positive)", async () => {
    onRpc("/web/webclient/version_info", () => expect.step("version_info"));

    await makeTestApp();

    // "online" event triggered when we're online
    browser.dispatchEvent(new Event("online"));
    await tick();
    expect.verifySteps([]);
    expect(getService(OfflinePlugin).isOffline()).toBe(false);

    // "offline" event triggered when we're already offline
    getService(OfflinePlugin).setOffline(true);
    await tick();
    expect(getService(OfflinePlugin).isOffline()).toBe(true);
    browser.dispatchEvent(new Event("offline"));
    await tick();
    expect.waitForSteps([]);
    expect(getService(OfflinePlugin).isOffline()).toBe(true);
});

test("Repeatedly check connection when going offline", async () => {
    patchWithCleanup(Math, {
        random: () => 1, // no jitter
    });

    const values = [false, true]; // simulate the 'back online status' after 2 'version_info' calls
    const mockVersionInfoRpc = () => {
        expect.step("version_info");
        const online = values.shift();
        if (online) {
            return new Response("true", { status: 200 });
        } else {
            return new Response("", { status: 502 });
        }
    };
    onRpc("/web/webclient/version_info", mockVersionInfoRpc, { pure: true });

    await makeTestApp();
    expect(getService(OfflinePlugin).isOffline()).toBe(false);

    // go offline
    getService(OfflinePlugin).setOffline(true);
    await tick();

    expect(getService(OfflinePlugin).isOffline()).toBe(true);
    await advanceTime(2000); // first version_info check
    expect(getService(OfflinePlugin).isOffline()).toBe(true);
    await advanceTime(3500); // second version_info check
    expect(getService(OfflinePlugin).isOffline()).toBe(false);
    expect.verifySteps(["version_info", "version_info"]);
});
