import { after, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { Deferred } from "@odoo/hoot-mock";
import { EventBus } from "@odoo/owl";
import { defineMenus, mountWebClient, onRpc } from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { makeLogger } from "@web/core/debug/debug_logger";
import { AppEvent } from "@web/core/events";
import { homeMenuService } from "@web/webclient/home_menu/home_menu_service";
import { WebClient } from "@web/webclient/webclient";

test("use stored menus, and update on load_menus return", async () => {
    const def = new Deferred();
    onRpc("/web/webclient/load_menus", () => def);
    defineMenus([
        {
            id: 1,
            appID: 1,
            actionID: 1,
            xmlid: "",
            name: "Partners",
            children: [],
            webIconData: "",
            webIcon: "bloop,bloop",
        },
        {
            id: 2,
            appID: 2,
            actionID: 2,
            xmlid: "",
            name: "CRM",
            children: [],
            webIconData: "",
            webIcon: "bloop,bloop",
        },
    ]);
    browser.localStorage.webclient_menus_version =
        "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0:7";
    browser.localStorage.webclient_menus = JSON.stringify({
        1: {
            id: 1,
            appID: 1,
            actionID: 1,
            xmlid: "",
            name: "Partners",
            children: [],
            webIconData: "",
            webIcon: "bloop,bloop",
        },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });
    const webClient = await mountWebClient({ WebClient: WebClient });
    webClient.env.bus.addEventListener(AppEvent.MENUS_APP_CHANGED, () =>
        expect.step("Update Menus"),
    );
    expect(".o_home_menu").toHaveCount(1);
    expect(".o_app").toHaveCount(1);
    expect.verifySteps([]);
    def.resolve();
    await animationFrame();
    expect(".o_app").toHaveCount(2);
    expect(JSON.parse(browser.localStorage.webclient_menus).menus).toEqual({
        1: {
            actionID: 1,
            appID: 1,
            children: [],
            id: 1,
            name: "Partners",
            webIcon: "bloop,bloop",
            webIconData: "",
            xmlid: "",
        },
        2: {
            actionID: 2,
            appID: 2,
            children: [],
            id: 2,
            name: "CRM",
            webIcon: "bloop,bloop",
            webIconData: "",
            xmlid: "",
        },
        root: {
            appID: "root",
            children: [1, 2],
            id: "root",
            name: "root",
        },
    });
    expect.verifySteps(["Update Menus"]);
});

test("home menu services can start independently in separate environments", async () => {
    const log = makeLogger("web.home_menu.test");
    const makeEnv = (name) => ({
        bus: new EventBus(),
        services: {
            action: {
                navigation: { epoch: 0 },
                doAction: async (action) => expect.step(`${name}:${action}`),
            },
        },
    });
    const first = homeMenuService.start(makeEnv("first"));
    after(() => first.destroy());
    const second = homeMenuService.start(makeEnv("second"));
    after(() => second.destroy());
    log.lifecycle("both environments started");
    first.hasHomeMenu = true;
    expect(second.hasHomeMenu).toBe(false);
    await second.toggle(true);
    expect.verifySteps(["second:menu"]);
});
