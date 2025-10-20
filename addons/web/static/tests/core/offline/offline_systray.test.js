import { WebClient } from "@web/webclient/webclient";

import { animationFrame, expect, test } from "@odoo/hoot";
import { contains, getService, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

test.tags("desktop");
test("offline systray item: basic rendering (desktop)", async () => {
    await mountWithCleanup(WebClient);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
    getService("offline").status.offline = true;

    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(1);
    expect(`.o_menu_systray .o_nav_entry:first`).toHaveText("Working offline");

    getService("offline").status.offline = false;
    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});

test.tags("mobile");
test("offline systray item: basic rendering (mobile)", async () => {
    await mountWithCleanup(WebClient);
    expect(`.o_menu_systray .o_nav_entry.fa-chain-broken`).toHaveCount(0);
    getService("offline").status.offline = true;

    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry.fa-chain-broken`).toHaveCount(1);
    expect(`.o_menu_systray .o_nav_entry:first`).toHaveAttribute("data-tooltip", "Working offline");

    getService("offline").status.offline = false;
    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry.fa-chain-broken`).toHaveCount(0);
});

test.tags("desktop");
test("offline systray item: click to check connection (desktop)", async () => {
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        return true;
    });
    await mountWithCleanup(WebClient);
    getService("offline").status.offline = true;

    await contains(`.o_menu_systray .o_nav_entry .fa-chain-broken`).click();
    expect.verifySteps(["version_info"]);
    expect(getService("offline").status.offline).toBe(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});

test.tags("mobile");
test("offline systray item: click to check connection (mobile)", async () => {
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        return true;
    });
    await mountWithCleanup(WebClient);
    getService("offline").status.offline = true;

    await contains(`.o_menu_systray .o_nav_entry.fa-chain-broken`).click();
    expect.verifySteps(["version_info"]);
    expect(getService("offline").status.offline).toBe(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});
