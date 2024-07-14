/** @odoo-module **/

import { getActionManagerServerData, doAction } from "@web/../tests/webclient/helpers";
import { homeMenuService } from "@web_enterprise/webclient/home_menu/home_menu_service";
import { ormService } from "@web/core/orm_service";
import { enterpriseSubscriptionService } from "@web_enterprise/webclient/home_menu/enterprise_subscription_service";
import { registry } from "@web/core/registry";
import { createEnterpriseWebClient } from "../helpers";
import { click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { shareUrlMenuItem } from "@web_enterprise/webclient/share_url/share_url";
import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { UserMenu } from "@web/webclient/user_menu/user_menu";

let serverData, target;
const serviceRegistry = registry.category("services");

QUnit.module("WebClient Mobile", (hooks) => {
    hooks.beforeEach(() => {
        serverData = getActionManagerServerData();
        target = getFixture();
        serviceRegistry.add("home_menu", homeMenuService);
        serviceRegistry.add("orm", ormService);
        serviceRegistry.add("enterprise_subscription", enterpriseSubscriptionService);
    });

    QUnit.test("scroll position is kept", async (assert) => {
        // This test relies on the fact that the scrollable element in mobile
        // is view's root node.
        const record = serverData.models.partner.records[0];
        serverData.models.partner.records = [];

        for (let i = 0; i < 80; i++) {
            const rec = Object.assign({}, record);
            rec.id = i + 1;
            rec.display_name = `Record ${rec.id}`;
            serverData.models.partner.records.push(rec);
        }

        // force the html node to be scrollable element
        const webClient = await createEnterpriseWebClient({ serverData });

        await doAction(webClient, 3); // partners in list/kanban
        assert.containsOnce(target, ".o_kanban_view");

        target.querySelector(".o_kanban_view").scrollTo(0, 123);
        await click(target.querySelectorAll(".o_kanban_record")[20]);
        assert.containsOnce(target, ".o_form_view");
        assert.containsNone(target, ".o_kanban_view");

        await click(target.querySelector(".o_control_panel .o_back_button"));
        assert.containsNone(target, ".o_form_view");
        assert.containsOnce(target, ".o_kanban_view");

        assert.strictEqual(target.querySelector(".o_kanban_view").scrollTop, 123);
    });

    QUnit.test(
        "Share URL item is not present in the user menu when screen is small",
        async function (assert) {
            patchWithCleanup(browser, {
                matchMedia: (media) => {
                    if (media === "(display-mode: standalone)") {
                        return { matches: true };
                    } else {
                        this._super();
                    }
                },
            });
            serviceRegistry.add("hotkey", hotkeyService);
            serviceRegistry.add("action", actionService);
            serviceRegistry.add("menu", menuService);

            const env = await makeTestEnv();

            registry.category("user_menuitems").add("share_url", shareUrlMenuItem);
            await mount(UserMenu, target, { env });
            assert.containsOnce(target, ".o_user_menu");
            // remove the "d-none" class to make the menu visible before interacting with it
            target.querySelector(".o_user_menu").classList.remove("d-none");
            await click(target.querySelector(".o_user_menu button"));
            assert.containsNone(
                target,
                ".o_user_menu .dropdown-item",
                "share button is not visible"
            );
        }
    );
});
