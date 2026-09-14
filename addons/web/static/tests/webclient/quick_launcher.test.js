import {
    advanceTime,
    animationFrame,
    beforeEach,
    click,
    describe,
    expect,
    freezeTime,
    hover,
    leave,
    queryAllTexts,
    test,
    unfreezeTime,
    waitFor,
} from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    defineActions,
    defineMenus,
    mountWebClient,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { user } from "@web/core/user";
import { menuUsage } from "@web/webclient/menus/menu_usage";
import { WebClient } from "@web/webclient/webclient";

describe.current.tags("desktop");

class TestClientAction extends Component {
    static template = xml`<div class="test_client_action">Client action</div>`;
    static props = ["*"];
}

beforeEach(() => {
    registry.category("actions").add("__quick_launcher_action__", TestClientAction);
});

function defineThreeApps() {
    defineActions(
        [1001, 1002, 1003].map((id) => ({
            id,
            tag: "__quick_launcher_action__",
            target: "main",
            type: "ir.actions.client",
        })),
    );
    defineMenus([
        { id: 0 },
        { id: 1, name: "App1", appID: 1, actionID: 1001, xmlid: "menu_1" },
        { id: 2, name: "App2", appID: 2, actionID: 1002, xmlid: "menu_2" },
        { id: 3, name: "App3", appID: 3, actionID: 1003, xmlid: "menu_3" },
    ]);
}

async function enterApp1() {
    await mountWebClient({ WebClient });
    await contains(".o_home_menu .o_app[data-menu-xmlid=menu_1]").click();
    expect(".o_home_menu").toHaveCount(0);
}

test("hovering the home toggle inside an app opens the quick launcher, pinned first", async () => {
    menuUsage.clear();
    patchWithCleanup(user, {
        settings: { ...user.settings, homemenu_config: '{"pinned":["menu_3"]}' },
    });
    defineThreeApps();
    await enterApp1();

    freezeTime();
    await hover(".o_menu_toggle");
    await advanceTime(399);
    expect(".o_quick_launcher").toHaveCount(0);
    await advanceTime(1);
    unfreezeTime();
    await animationFrame();
    expect(".o_quick_launcher .o_app").toHaveCount(3);
    expect(queryAllTexts(".o_quick_launcher .o_caption")).toEqual([
        "App3",
        "App1",
        "App2",
    ]);

    await click(".o_quick_launcher .o_app[data-menu-xmlid=menu_2]");
    await animationFrame();
    expect(".o_quick_launcher").toHaveCount(0);
    await waitFor(".o_menu_brand:contains(App2)");
    menuUsage.clear();
});

test("leaving the toggle before the delay, or clicking it, opens no launcher", async () => {
    defineThreeApps();
    await enterApp1();

    freezeTime();
    await hover(".o_menu_toggle");
    await advanceTime(200);
    await leave();
    await advanceTime(400);
    unfreezeTime();
    expect(".o_quick_launcher").toHaveCount(0);

    await hover(".o_menu_toggle");
    await click(".o_menu_toggle");
    await advanceTime(400);
    await animationFrame();
    expect(".o_quick_launcher").toHaveCount(0);
    expect(".o_home_menu").toHaveCount(1, {
        message: "the click went to the home menu",
    });
});

test("typing in the quick launcher hands off to the palette's menu search", async () => {
    defineThreeApps();
    await enterApp1();
    await hover(".o_menu_toggle");
    await advanceTime(400);
    await animationFrame();

    const input = /** @type {HTMLInputElement} */ (
        document.querySelector(".o_quick_launcher_search")
    );
    input.value = "app";
    input.dispatchEvent(new InputEvent("input", { bubbles: true }));
    await animationFrame();
    expect(".o_quick_launcher").toHaveCount(0);
    expect(".o_command_palette").toHaveCount(1);
    expect(".o_command_palette_search input").toHaveValue("app");
    expect(".o_command_palette_search .o_namespace:first").toHaveText("/");
});

test("All apps in the quick launcher opens the home menu", async () => {
    onRpc("set_res_users_settings", () => ({}));
    defineThreeApps();
    await enterApp1();
    await hover(".o_menu_toggle");
    await advanceTime(400);
    await animationFrame();
    await click(".o_quick_launcher_all");
    await animationFrame();
    expect(".o_quick_launcher").toHaveCount(0);
    expect(".o_home_menu").toHaveCount(1);
});
