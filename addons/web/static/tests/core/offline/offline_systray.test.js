import { WebClient } from "@web/webclient/webclient";

import { expect, test } from "@odoo/hoot";
import {
    contains,
    getService,
    mountWithCleanup,
    mockOffline,
    onRpc,
} from "@web/../tests/web_test_helpers";

test.tags("desktop");
test("offline systray item: basic rendering (desktop)", async () => {
    const setOffline = mockOffline();
    await mountWithCleanup(WebClient);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
    await setOffline(true);

    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(1);
    expect(`.o_menu_systray .o_nav_entry:first`).toHaveText("Working offline");

    await setOffline(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});

test.tags("mobile");
test("offline systray item: basic rendering (mobile)", async () => {
    const setOffline = mockOffline();
    await mountWithCleanup(WebClient);
    expect(`.o_menu_systray .o_nav_entry.fa-chain-broken`).toHaveCount(0);
    await setOffline(true);

    expect(`.o_menu_systray .o_nav_entry.fa-chain-broken`).toHaveCount(1);
    expect(`.o_menu_systray .o_nav_entry:first`).toHaveAttribute("data-tooltip", "Working offline");

    await setOffline(false);
    expect(`.o_menu_systray .o_nav_entry.fa-chain-broken`).toHaveCount(0);
});

test.tags("desktop");
test("offline systray item: click to check connection (desktop)", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        return true;
    });
    await mountWithCleanup(WebClient);
    await setOffline(true);

    await contains(`.o_menu_systray .o_nav_entry .fa-chain-broken`).click();
    expect.verifySteps(["version_info"]);
    expect(getService("offline").offline).toBe(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});

test.tags("mobile");
test("offline systray item: click to check connection (mobile)", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        return true;
    });
    await mountWithCleanup(WebClient);
    await setOffline(true);

    await contains(`.o_menu_systray .o_nav_entry.fa-chain-broken`).click();
    expect.verifySteps(["version_info"]);
    expect(getService("offline").offline).toBe(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});
