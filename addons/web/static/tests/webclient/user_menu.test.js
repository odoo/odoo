// @ts-check

import "@web/webclient/user_menu/user_menu_items";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    click,
    queryAllAttributes,
    queryAllProperties,
    queryAllTexts,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    clearRegistry,
    contains,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    stepAllNetworkCalls,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { getOrigin } from "@web/core/utils/urls";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

const userMenuRegistry = registry.category("user_menuitems");
const preferencesItem = userMenuRegistry.get("preferences");
const odooAccountItem = userMenuRegistry.get("odoo_account");

describe.current.tags("desktop");

beforeEach(async () => {
    serverState.partnerName = "Sauron";
    clearRegistry(userMenuRegistry);
});

test("can be rendered", async () => {
    patchWithCleanup(user, { writeDate: "2024-01-01 12:00:00" });
    userMenuRegistry.add("bad_item", () => ({
        type: "item",
        id: "bad",
        description: "Bad",
        callback: () => {
            expect.step("callback bad_item");
        },
        sequence: 10,
    }));
    userMenuRegistry.add("ring_item", () => ({
        type: "item",
        id: "ring",
        description: "Ring",
        callback: () => {
            expect.step("callback ring_item");
        },
        sequence: 5,
    }));
    userMenuRegistry.add("frodo_item", () => ({
        type: "switch",
        id: "frodo",
        description: "Frodo",
        callback: () => {
            expect.step("callback frodo_item");
        },
        sequence: 11,
    }));
    userMenuRegistry.add("separator", () => ({
        type: "separator",
        sequence: 15,
    }));
    userMenuRegistry.add("invisible_item", () => ({
        type: "item",
        id: "hidden",
        description: "Hidden Power",
        callback: () => {},
        sequence: 5,
        hide: true,
    }));
    userMenuRegistry.add("eye_item", () => ({
        type: "item",
        id: "eye",
        description: "Eye",
        callback: () => {
            expect.step("callback eye_item");
        },
    }));
    await mountWithCleanup(UserMenu);
    expect("img.o_user_avatar").toHaveCount(1);
    expect("img.o_user_avatar").toHaveAttribute(
        "data-src",
        `${getOrigin()}/web/image/res.partner/17/avatar_128?unique=1704106800000`,
    );
    expect(".dropdown-menu .dropdown-item").toHaveCount(0);
    await contains("button.dropdown-toggle").click();
    expect(".dropdown-menu .dropdown-item").toHaveCount(4);
    expect(".dropdown-menu .dropdown-item input.form-check-input").toHaveCount(1);
    expect("div.dropdown-divider").toHaveCount(1);
    expect(queryAllProperties(".dropdown-menu > *", "tagName")).toEqual([
        "SPAN",
        "SPAN",
        "SPAN",
        "DIV",
        "SPAN",
    ]);
    expect(queryAllAttributes(".dropdown-menu .dropdown-item", "data-menu")).toEqual([
        "ring",
        "bad",
        "frodo",
        "eye",
    ]);
    expect(queryAllTexts(".dropdown-menu .dropdown-item")).toEqual([
        "Ring",
        "Bad",
        "Frodo",
        "Eye",
    ]);

    for (let i = 0; i < 4; i++) {
        await click(`.dropdown-menu .dropdown-item:eq(${i})`);

        await click("button.dropdown-toggle");
        await animationFrame();
    }

    expect.verifySteps([
        "callback ring_item",
        "callback bad_item",
        "callback frodo_item",
        "callback eye_item",
    ]);
});

test("display the correct name in debug mode", async () => {
    serverState.debug = "1";
    await mountWithCleanup(UserMenu);
    expect("img.o_user_avatar").toHaveCount(1);
    expect("small.oe_topbar_name").toHaveCount(1);
    expect(".oe_topbar_name").toHaveText("Sauron" + "\n" + "test");
});

test("can execute the callback of settings", async () => {
    onRpc("action_get", () => ({
        name: "Change My Preferences",
        res_id: 0,
    }));
    mockService("action", {
        async doAction(actionId) {
            expect.step(String(actionId.res_id));
            expect.step(actionId.name);
        },
    });

    userMenuRegistry.add("preferences", preferencesItem);
    await mountWithCleanup(UserMenu);
    await contains("button.dropdown-toggle").click();
    expect(".dropdown-menu .dropdown-item").toHaveCount(1);
    expect(".dropdown-menu .dropdown-item").toHaveText("My Preferences");
    await contains(".dropdown-menu .dropdown-item").click();
    expect.verifySteps(["7", "Change My Preferences"]);
});

test("click on odoo account item", async () => {
    patchWithCleanup(browser, {
        open: (url) => {
            expect.step(`open ${url}`);
            return window;
        },
    });
    userMenuRegistry.add("odoo_account", odooAccountItem);
    await mountWithCleanup(UserMenu);
    onRpc("/web/session/account", () => "https://account-url.com");
    stepAllNetworkCalls();
    await contains("button.dropdown-toggle").click();
    expect(".o-dropdown--menu .dropdown-item").toHaveCount(1);
    expect(".o-dropdown--menu .dropdown-item").toHaveText("My Odoo.com Account");
    await contains(".o-dropdown--menu .dropdown-item").click();
    expect.verifySteps(["/web/session/account", "open https://account-url.com"]);
});

test("can use component as registry item", async () => {
    class ExampleComponent extends Component {
        static template = xml`<span class='component-class'>Example Component</span>`;
        static props = ["*"];
    }
    userMenuRegistry.add("component-item", () => ({
        type: "component",
        contentComponent: ExampleComponent,
        sequence: 10,
    }));
    await mountWithCleanup(UserMenu);
    await contains("button.dropdown-toggle").click();
    expect(".o-dropdown--menu span.component-class").toHaveText("Example Component");
});

test("sequence 0 sorts first, not as the default 100", async () => {
    userMenuRegistry.add("last_item", () => ({
        type: "item",
        id: "last",
        description: "Last",
        callback: () => {},
        sequence: 200,
    }));
    userMenuRegistry.add("default_item", () => ({
        type: "item",
        id: "default",
        description: "Default",
        callback: () => {},
    }));
    userMenuRegistry.add("first_item", () => ({
        type: "item",
        id: "first",
        description: "First",
        callback: () => {},
        sequence: 0,
    }));
    await mountWithCleanup(UserMenu);
    await contains("button.dropdown-toggle").click();
    expect(queryAllTexts(".o-dropdown--menu .dropdown-item")).toEqual([
        "First",
        "Default",
        "Last",
    ]);
});

test("the user menu toggle is named as a menu, not as an image", async () => {
    await mountWithCleanup(UserMenu);
    expect(".o_user_menu button").toHaveAttribute("aria-label", "User menu");
    expect(".o_user_menu button img").toHaveAttribute("alt", "");
});

test("a throwing provider does not remove other user menu entries", async () => {
    userMenuRegistry.add("broken", () => {
        throw new Error("broken extension");
    });
    userMenuRegistry.add("healthy", () => ({
        type: "item",
        description: "Healthy",
        callback() {},
    }));
    await mountWithCleanup(UserMenu);
    await contains(".o_user_menu button").click();
    expect(".o-dropdown--menu").toHaveText("Healthy");
});
