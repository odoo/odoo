import { Component, useState, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { rpc } from "@web/core/network/rpc";

import { advanceTime, animationFrame, expect, test, tick } from "@odoo/hoot";
import {
    getService,
    makeMockEnv,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

test("RPC:RESPONSE: rpc returning a status 502", async () => {
    expect.errors(1);

    onRpc("/rpc/offline", () => new Response("", { status: 502 }), { pure: true });

    const env = await makeMockEnv();
    expect(env.services.offline.offline).toBe(false);

    rpc("/rpc/offline");
    await animationFrame();
    expect(env.services.offline.offline).toBe(true);

    expect.verifyErrors([
        `Error: Connection to "/rpc/offline" couldn't be established or was interrupted`,
    ]);
});

test("RPC:RESPONSE: any succesfull rpc turns offline off", async () => {
    onRpc("/rpc/thatworks", () => true);

    const env = await makeMockEnv();
    env.services.offline.offline = true;
    await tick();
    expect(env.services.offline.offline).toBe(true);

    await rpc("/rpc/thatworks");
    expect(env.services.offline.offline).toBe(false);
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

    const env = await makeMockEnv();

    offline = true;
    browser.dispatchEvent(new Event("offline"));
    await tick();
    expect.verifySteps(["version_info"]);
    expect(env.services.offline.offline).toBe(true);

    offline = false;
    browser.dispatchEvent(new Event("online"));
    await tick();
    expect.verifySteps(["version_info"]);
    expect(env.services.offline.offline).toBe(false);
});

test("'offline' and 'online' events fired on window (false positive)", async () => {
    onRpc("/web/webclient/version_info", () => expect.step("version_info"));

    const env = await makeMockEnv();

    // "online" event triggered when we're online
    browser.dispatchEvent(new Event("online"));
    await tick();
    expect.verifySteps([]);
    expect(env.services.offline.offline).toBe(false);

    // "offline" event triggered when we're already offline
    env.services.offline.offline = true;
    await tick();
    expect(env.services.offline.offline).toBe(true);
    browser.dispatchEvent(new Event("offline"));
    await tick();
    expect.waitForSteps([]);
    expect(env.services.offline.offline).toBe(true);
});

test("offlineUI: disable interactive elements except [data-available-offline]", async () => {
    class Root extends Component {
        static template = xml`
            <div>
                <button type="button" class="button_to_disable"> Disable this button </button>
                <button type="button" class="button_available_offline" data-available-offline=""> Don't disable this button </button>
                <input type="checkbox" name="checkbox" class="checkbox_to_disable"/>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    expect(`.button_to_disable`).not.toHaveAttribute("disabled");
    expect(`.button_available_offline`).not.toHaveAttribute("disabled");
    expect(`.checkbox_to_disable`).not.toHaveAttribute("disabled");

    getService("offline").offline = true;
    expect(`.button_to_disable`).toHaveAttribute("disabled");
    expect(`.button_available_offline`).not.toHaveAttribute("disabled");
    expect(`.checkbox_to_disable`).toHaveAttribute("disabled");
    expect(`.button_to_disable`).toHaveClass("o_disabled_offline");
    expect(`.button_available_offline`).not.toHaveClass("o_disabled_offline");
    expect(`.checkbox_to_disable`).toHaveClass("o_disabled_offline");

    getService("offline").offline = false;
    expect(`.button_to_disable`).not.toHaveAttribute("disabled");
    expect(`.button_available_offline`).not.toHaveAttribute("disabled");
    expect(`.checkbox_to_disable`).not.toHaveAttribute("disabled");
});

test("offlineUI: don't disable already disabled elements", async () => {
    class Root extends Component {
        static template = xml`
            <div>
                <button type="button" class="button" disabled="disabled"> Disabled button </button>
                <input type="checkbox" class="checkbox" disabled="disabled"/>
            </div>
        `;
        static props = ["*"];
    }

    await mountWithCleanup(Root);
    expect(`.button`).toHaveAttribute("disabled");
    expect(`.checkbox`).toHaveAttribute("disabled");

    getService("offline").offline = true;
    expect(`.button`).toHaveAttribute("disabled");
    expect(`.checkbox`).toHaveAttribute("disabled");
    expect(`.button`).not.toHaveClass("o_disabled_offline");
    expect(`.checkbox`).not.toHaveClass("o_disabled_offline");

    getService("offline").offline = false;
    expect(`.button`).toHaveAttribute("disabled");
    expect(`.checkbox`).toHaveAttribute("disabled");
});

test("offlineUI: react to [data-available-offline] attribute changes", async () => {
    let state;
    class Root extends Component {
        static template = xml`
            <div>
                <button type="button" class="btn1" t-att="{ 'data-available-offline': state.btn1Available }">
                    First
                </button>
                <button type="button" class="btn2" t-att="{ 'data-available-offline': state.btn2Available }">
                    Second
                </button>
            </div>
        `;
        static props = ["*"];

        setup() {
            this.state = useState({
                btn1Available: true,
                btn2Available: false,
            });
            state = this.state;
        }
    }

    await mountWithCleanup(Root);
    expect(".btn1").not.toHaveAttribute("disabled");
    expect(".btn2").not.toHaveAttribute("disabled");

    getService("offline").offline = true;
    expect(".btn1").not.toHaveAttribute("disabled");
    expect(".btn2").toHaveAttribute("disabled");

    state.btn1Available = false;
    state.btn2Available = true;
    await animationFrame();
    expect(".btn1").toHaveAttribute("disabled");
    expect(".btn2").not.toHaveAttribute("disabled");
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

    const env = await makeMockEnv();
    expect(env.services.offline.offline).toBe(false);

    // go offline
    env.services.offline.offline = true;
    await tick();

    expect(env.services.offline.offline).toBe(true);
    await advanceTime(2000); // first version_info check
    expect(env.services.offline.offline).toBe(true);
    await advanceTime(3500); // second version_info check
    expect(env.services.offline.offline).toBe(false);
    expect.verifySteps(["version_info", "version_info"]);
});

test("isAvailableOffline", async () => {
    const env = await makeMockEnv();
    expect(env.services.offline.offline).toBe(false);

    await env.services.offline.setAvailableOffline(1, "list", { search: { key: 1 } });
    await env.services.offline.setAvailableOffline(1, "form", { resId: 1 });

    // go offline
    env.services.offline.offline = true;
    await tick();
    expect(env.services.offline.offline).toBe(true);

    expect(env.services.offline.isAvailableOffline(1)).toBe(true);
    expect(env.services.offline.isAvailableOffline(4)).toBe(false);

    expect(env.services.offline.isAvailableOffline(1, "list")).toBe(true);
    expect(env.services.offline.isAvailableOffline(1, "kanban")).toBe(false);

    expect(env.services.offline.isAvailableOffline(1, "list", 1)).toBe(true);
    expect(env.services.offline.isAvailableOffline(1, "kanban", 3)).toBe(false);
});

test("getAvailableSearches", async () => {
    const env = await makeMockEnv();
    const offline = env.services.offline;
    expect(offline.offline).toBe(false);

    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "2" } });
    await offline.setAvailableOffline(1, "kanban", { search: { key: "oui" } });
    await offline.setAvailableOffline(2, "kanban", { search: { key: "8" } });

    // go offline
    offline.offline = true;
    await tick();
    expect(offline.offline).toBe(true);

    expect(await offline.getAvailableSearches(1, "list")).toEqual([{ key: "2" }, { key: "1" }]);
    expect(await offline.getAvailableSearches(1, "kanban")).toEqual([{ key: "oui" }]);
    expect(await offline.getAvailableSearches(2, "kanban")).toEqual([{ key: "8" }]);
});

test("getAvailableSearches (searches order)", async () => {
    const env = await makeMockEnv();
    const offline = env.services.offline;
    expect(offline.offline).toBe(false);

    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "2" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "2" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "3" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "1" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "4" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "3" } });
    await offline.setAvailableOffline(1, "list", { search: { key: "5" } });

    // go offline
    offline.offline = true;
    await tick();
    expect(offline.offline).toBe(true);

    expect(await offline.getAvailableSearches(1, "list")).toEqual([
        { key: "1" }, // accessed 3 times
        { key: "3" }, // accessed twice
        { key: "2" }, // accessed twice (less recently)
        { key: "5" }, // accessed once
        { key: "4" }, // accessed once (less recently)
    ]);
});
