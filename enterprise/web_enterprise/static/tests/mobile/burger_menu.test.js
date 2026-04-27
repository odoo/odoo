import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, queryAll } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { defineActions, defineMenus, mountWithCleanup } from "@web/../tests/web_test_helpers";

import { Component, onMounted, xml } from "@odoo/owl";

import { registry } from "@web/core/registry";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

const actionRegistry = registry.category("actions");

const queryAllRoot = (selector) => queryAll(selector, { root: document.body });

class TestClientAction extends Component {
    static template = xml`
            <div class="test_client_action">
                ClientAction_<t t-esc="props.action.params?.description"/>
            </div>`;
    static props = ["*"];
    setup() {
        onMounted(() => this.env.config.setDisplayName(`Client action ${this.props.action.id}`));
    }
}

describe.current.tags("mobile");

beforeEach(() => {
    defineMenus([
        {
            id: 1,
            name: "App1",
            appID: 1,
            actionID: 1001,
            xmlid: "menu_1",
        },
    ]);
});

test("Burger Menu on home menu", async () => {
    expect.assertions(5);

    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();
    expect(queryAllRoot(".o_burger_menu")).toHaveCount(0);
    expect(queryAllRoot(".o_home_menu")).toBeVisible();

    await click(queryAllRoot(".o_mobile_menu_toggle"));
    await runAllTimers();
    await animationFrame();
    expect(queryAllRoot(".o_burger_menu")).toHaveCount(1);
    expect(queryAllRoot(".o_user_menu_mobile")).toHaveCount(1);
    await click(queryAllRoot(".o_sidebar_close"));
    await animationFrame();
    expect(".o_burger_menu").toHaveCount(0);
});

test("Burger Menu on home menu over an App", async () => {
    expect.assertions(5);

    actionRegistry.add("__test__client__action__", TestClientAction);

    defineMenus([
        {
            id: 1,
            children: [
                {
                    id: 99,
                    name: "SubMenu",
                    appID: 1,
                    actionID: 1002,
                    webIconData: undefined,
                    webIcon: false,
                },
            ],
        },
    ]);

    defineActions([
        {
            id: 1001,
            tag: "__test__client__action__",
            target: "main",
            type: "ir.actions.client",
            params: { description: "Id 1" },
        },
    ]);

    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    await click(queryAllRoot(".o_draggable:first-of-type .o_app"));
    await animationFrame();
    await click(queryAllRoot(".o_menu_toggle"));
    await animationFrame();
    await click(queryAllRoot(".o_sidebar_topbar a.btn-primary"));
    await animationFrame();

    expect(queryAllRoot(".o_burger_menu")).toHaveCount(0);
    expect(queryAllRoot(".o_home_menu")).toBeVisible();

    await click(queryAllRoot(".o_mobile_menu_toggle"));
    await animationFrame();
    expect(queryAllRoot(".o_burger_menu")).toHaveCount(1);
    expect(queryAllRoot(".o_burger_menu nav.o_burger_menu_content li")).toHaveCount(0);
    expect(queryAllRoot(".o_burger_menu_content")).not.toHaveClass("o_burger_menu_dark");
});
