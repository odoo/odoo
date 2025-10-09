import { Component, xml } from "@odoo/owl";
import {
    makeMockEnv,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "../web_test_helpers";
import { expect, test } from "@odoo/hoot";
import { ConnectionLostError, rpc } from "@web/core/network/rpc";
import { advanceTime, animationFrame } from "@odoo/hoot-dom";
import { WebClient } from "@web/webclient/webclient";

test("handle CONNECTION_LOST_ERROR", async () => {
    expect.errors(1);
    mockService("notification", {
        add(message) {
            expect.step(`create (${message})`);
            return () => {
                expect.step(`close`);
            };
        },
    });
    const values = [false, true]; // simulate the 'back online status' after 2 'version_info' calls
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        const online = values.shift();
        if (online) {
            return true;
        } else {
            return Promise.reject();
        }
    });

    const env = await makeMockEnv();
    expect(env.services.offline.offline).toBe(false);
    const error = new ConnectionLostError("/fake_url");
    Promise.reject(error);
    await animationFrame();
    expect(env.services.offline.offline).toBe(true);
    patchWithCleanup(Math, {
        random: () => 0,
    });
    // wait for timeouts
    await advanceTime(2000);
    await advanceTime(3500);
    expect(env.services.offline.offline).toBe(false);
    expect.verifySteps([
        "create (Connection lost)",
        "version_info",
        "version_info",
        "close",
        "create (Connection restored)",
    ]);
    expect.verifyErrors([
        `Error: Connection to "/fake_url" couldn't be established or was interrupted`,
    ]);
});

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

test("any succesfull rpc will turn offline off", async () => {
    onRpc("/rpc/thatworks", () => true);
    const env = await makeMockEnv();
    env.services.offline.offline = true;

    expect(env.services.offline.offline).toBe(true);

    await rpc("/rpc/thatworks");

    expect(env.services.offline.offline).toBe(false);
});

test("disable/enable all buttons and checkbox", async () => {
    class Root extends Component {
        static template = xml`
            <div>
                <button type="button" class="to_disable"> Disable this button </button>
                <button type="button" class="dont_disable" t-att-data-offline-available="1"> Don't disable this button </button>
                <input type="checkbox" name="checkbox" class="the_checkbox"/>
            
            </div>
        `;
        static props = ["*"];
    }

    const comp = await mountWithCleanup(Root);
    expect(`.to_disable`).not.toHaveAttribute("disabled");
    expect(`.dont_disable`).not.toHaveAttribute("disabled");
    expect(`.the_checkbox`).not.toHaveAttribute("disabled");

    comp.env.services.offline.offline = true;
    expect(`.to_disable`).toHaveAttribute("disabled");
    expect(`.dont_disable`).not.toHaveAttribute("disabled");
    expect(`.the_checkbox`).toHaveAttribute("disabled");

    comp.env.services.offline.offline = false;
    expect(`.to_disable`).not.toHaveAttribute("disabled");
    expect(`.dont_disable`).not.toHaveAttribute("disabled");
    expect(`.the_checkbox`).not.toHaveAttribute("disabled");
});

test("offline systray show if offline", async () => {
    const webclient = await mountWithCleanup(WebClient);
    expect(`.o_menu_systray div[title="offline"]`).toHaveCount(0);
    webclient.env.services.offline.offline = true;

    await animationFrame();
    expect(`.o_menu_systray div[title="offline"]`).toHaveCount(1);

    webclient.env.services.offline.offline = false;
    await animationFrame();
    expect(`.o_menu_systray div[title="offline"]`).toHaveCount(0);
});
