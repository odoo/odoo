/** @odoo-module **/
import { click, nextTick } from "@web/../tests/helpers/utils";
import {
    createWebClient,
    doAction,
    getActionManagerServerData,
} from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { BurgerMenu } from "@web/webclient/burger_menu/burger_menu";
import { companyService } from "@web/webclient/company_service";

/**
 * Note: The asserts are all based on document.body (instead of getFixture() by example) because
 * the burger menu is porteled into the dom and is not part of the qunit fixture.
 */

let serverData;

const serviceRegistry = registry.category("services");

QUnit.module("Burger Menu", {
    beforeEach() {
        serverData = getActionManagerServerData();

        serviceRegistry.add("company", companyService);

        registry.category("systray").add("burger_menu", {
            Component: BurgerMenu,
        });
    },
});

QUnit.test("Burger menu can be opened and closed", async (assert) => {
    assert.expect(2);

    await createWebClient({ serverData });

    await click(document.body, ".o_mobile_menu_toggle");
    assert.containsOnce(document.body, ".o_burger_menu");

    await click(document.body, ".o_burger_menu_close");
    assert.containsNone(document.body, ".o_burger_menu");
});

QUnit.test("Burger Menu on an App", async (assert) => {
    assert.expect(7);

    serverData.menus[1].children = [99];
    serverData.menus[99] = {
        id: 99,
        children: [],
        name: "SubMenu",
        appID: 1,
        actionID: 1002,
        xmlid: "",
        webIconData: undefined,
        webIcon: false,
    };

    await createWebClient({ serverData });
    await click(document.body, ".o_navbar_apps_menu .dropdown-toggle");
    await click(document.body, ".o_app:nth-of-type(2)");

    assert.containsNone(document.body, ".o_burger_menu");

    await click(document.body, ".o_mobile_menu_toggle");
    assert.containsOnce(document.body, ".o_burger_menu");
    assert.containsOnce(document.body, ".o_burger_menu nav.o_burger_menu_content li");
    assert.strictEqual(
        document.body.querySelector(".o_burger_menu nav.o_burger_menu_content li").textContent,
        "SubMenu"
    );
    assert.hasClass(document.body.querySelector(".o_burger_menu_content"), "o_burger_menu_app");

    await click(document.body, ".o_burger_menu_topbar");
    assert.doesNotHaveClass(
        document.body.querySelector(".o_burger_menu_content"),
        "o_burger_menu_dark"
    );

    await click(document.body, ".o_burger_menu_topbar");
    assert.hasClass(document.body.querySelector(".o_burger_menu_content"), "o_burger_menu_app");
});

QUnit.test("Burger Menu on an App without SubMenu", async (assert) => {
    assert.expect(4);

    await createWebClient({ serverData });
    await click(document.body, ".o_navbar_apps_menu .dropdown-toggle");
    await click(document.body, ".o_app:nth-of-type(2)");

    assert.containsNone(document.body, ".o_burger_menu");

    await click(document.body, ".o_mobile_menu_toggle");
    assert.containsOnce(document.body, ".o_burger_menu");
    assert.containsOnce(document.body, ".o_user_menu_mobile");
    await click(document.body, ".o_burger_menu_close");
    assert.containsNone(document.body, ".o_burger_menu");
});

QUnit.test("Burger menu closes when an action is requested", async (assert) => {
    assert.expect(3);

    const wc = await createWebClient({ serverData });

    await click(document.body, ".o_mobile_menu_toggle");
    assert.containsOnce(document.body, ".o_burger_menu");

    await doAction(wc, 1);
    assert.containsNone(document.body, ".o_burger_menu");
    assert.containsOnce(document.body, ".o_kanban_view");
});

QUnit.test("Burger menu closes when click on menu item", async (assert) => {
    serverData.actions[1].target = "new";
    serverData.menus[1].children = [99];
    serverData.menus[99] = {
        id: 99,
        children: [],
        name: "SubMenu",
        appID: 1,
        actionID: 1,
        xmlid: "",
        webIconData: undefined,
        webIcon: false,
    };
    await createWebClient({ serverData });
    await click(document.body, ".o_navbar_apps_menu .dropdown-toggle");
    await click(document.body, ".o_app:nth-of-type(2)");

    assert.containsNone(document.body, ".o_burger_menu");

    await click(document.body, ".o_mobile_menu_toggle");
    assert.containsOnce(document.body, ".o_burger_menu");
    assert.strictEqual(
        document.body.querySelector(".o_burger_menu nav.o_burger_menu_content li").textContent,
        "SubMenu"
    );
    await click(document.body, ".o_burger_menu nav.o_burger_menu_content li");
    await nextTick();
    assert.containsNone(document.body, ".o_burger_menu");
});
