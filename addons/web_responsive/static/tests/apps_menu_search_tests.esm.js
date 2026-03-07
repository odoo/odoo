/* global QUnit */
/* eslint init-declarations: "warn" */
/* Copyright 2023 Taras Shabaranskyi
 * License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl). */

import {Component, xml} from "@odoo/owl";
import {click, getFixture, mount, patchWithCleanup} from "@web/../tests/helpers/utils";
import {NavBar} from "@web/webclient/navbar/navbar";
import {actionService} from "@web/webclient/actions/action_service";
import {browser} from "@web/core/browser/browser";
import {hotkeyService} from "@web/core/hotkeys/hotkey_service";
import {makeTestEnv} from "@web/../tests/helpers/mock_env";
import {menuService} from "@web/webclient/menus/menu_service";
import {notificationService} from "@web/core/notifications/notification_service";
import {registry} from "@web/core/registry";
import {uiService} from "@web/core/ui/ui_service";

const serviceRegistry = registry.category("services");

class MySystrayItem extends Component {}

MySystrayItem.template = xml`<li class="my-item">my item</li>`;
let baseConfig = {};
let target = {};

QUnit.module("AppsMenu Search", {
    async beforeEach() {
        target = getFixture();
        serviceRegistry.add("menu", menuService);
        serviceRegistry.add("action", actionService);
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        patchWithCleanup(browser, {
            setTimeout: (handler, delay, ...args) => handler(...args),
            clearTimeout: () => undefined,
        });
        const menus = {
            root: {id: "root", children: [1, 2], name: "root", appID: "root"},
            1: {id: 1, children: [], name: "App0", appID: 1, xmlid: "menu_1"},
            2: {id: 2, children: [], name: "App1", appID: 2, xmlid: "menu_2"},
        };
        const serverData = {menus};
        baseConfig = {serverData};
    },
});

QUnit.test("can be rendered", async (assert) => {
    const env = await makeTestEnv(baseConfig);
    await mount(NavBar, target, {env});
    await click(target, "button.o_grid_apps_menu__button");
    assert.containsOnce(target, ".app-menu-container .search-input");
});
