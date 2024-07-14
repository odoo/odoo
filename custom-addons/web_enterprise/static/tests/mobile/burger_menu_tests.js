/** @odoo-module **/
import { click } from "@web/../tests/helpers/utils";
import { getActionManagerServerData } from "@web/../tests/webclient/helpers";
import { registry } from "@web/core/registry";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { EnterpriseBurgerMenu } from "@web_enterprise/webclient/burger_menu/burger_menu";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { companyService } from "@web/webclient/company_service";
import { ormService } from "@web/core/orm_service";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";

/**
 * Note: The asserts are all based on document.body (instead of getFixture() by example) because
 * the burger menu is porteled into the dom and is not part of the qunit fixture.
 */

let serverData;

const serviceRegistry = registry.category("services");

QUnit.module("Burger Menu Enterprise", {
    beforeEach() {
        serverData = getActionManagerServerData();

        serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);
        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("company", companyService);
        serviceRegistry.add("home_menu", homeMenuService);

        registry.category("systray").add("burger_menu", {
            Component: EnterpriseBurgerMenu,
        });
    },
});

QUnit.test("Burger Menu on home menu", async (assert) => {
    assert.expect(5);

    await createEnterpriseWebClient({ serverData });
    assert.containsNone(document.body, ".o_burger_menu");
    assert.isVisible(document.body.querySelector(".o_home_menu"));

    await click(document.body, ".o_mobile_menu_toggle");
    assert.containsOnce(document.body, ".o_burger_menu");
    assert.containsOnce(document.body, ".o_user_menu_mobile");
    await click(document.body, ".o_burger_menu_close");
    assert.containsNone(document.body, ".o_burger_menu");
});

QUnit.test("Burger Menu on home menu over an App", async (assert) => {
    assert.expect(5);

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

    await createEnterpriseWebClient({ serverData });
    await click(document.body, ".o_draggable:first-of-type .o_app");
    await click(document.body, ".o_menu_toggle");

    assert.containsNone(document.body, ".o_burger_menu");
    assert.isVisible(document.body.querySelector(".o_home_menu"));

    await click(document.body, ".o_mobile_menu_toggle");
    assert.containsOnce(document.body, ".o_burger_menu");
    assert.containsNone(document.body, ".o_burger_menu nav.o_burger_menu_content li");
    assert.doesNotHaveClass(
        document.body.querySelector(".o_burger_menu_content"),
        "o_burger_menu_dark"
    );
});
