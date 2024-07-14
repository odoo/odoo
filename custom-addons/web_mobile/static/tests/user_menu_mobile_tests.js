/** @odoo-module **/

import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { UserMenu } from "@web/webclient/user_menu/user_menu";
import { shortcutItem, switchAccountItem } from "../src/js/user_menu_items";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { makeFakeNotificationService } from "@web/../tests/helpers/mock_services";
import { click as _click, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { menuService } from "@web/webclient/menus/menu_service";
import { actionService } from "@web/webclient/actions/action_service";

import mobile from "@web_mobile/js/services/core";

const serviceRegistry = registry.category("services");
const userMenuRegistry = registry.category("user_menuitems");
const MY_IMAGE =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";
let target;


// The UserMenu has a d-none class which is overriden, purely by bootstrap
// by d-x-block classes when the screen has a minimum size.
// To avoid problems, we always skip the visibility check by default when clicking
const click = (el, selector, skipVisibility) => {
    if (skipVisibility === undefined) {
        skipVisibility = true;
    }
    return _click(el, selector, skipVisibility);
};
QUnit.module("UserMenu", {
    async beforeEach() {
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("action", actionService);
        serviceRegistry.add("menu", menuService);
        target = getFixture();
    },
});

QUnit.test("can execute the callback of addHomeShortcut on an App", async (assert) => {
    assert.expect(8)
    patchWithCleanup(mobile.methods, {
        addHomeShortcut({ title, shortcut_url, web_icon }) {
            assert.step("should call addHomeShortcut");
            assert.strictEqual(title, document.title);
            assert.strictEqual(shortcut_url, document.URL);
            assert.strictEqual(web_icon, MY_IMAGE);
        }
    });
    const menus = {
        root: { id: "root", children: [1], name: "root", appID: "root" },
        1: { id: 1, children: [], name: "App0", appID: 1, webIconData: `data:image/png;base64,${MY_IMAGE}` },
    };
    const baseConfig = { serverData: { menus } };
    const env = await makeTestEnv(baseConfig);

    userMenuRegistry.add("web_mobile.shortcut", shortcutItem);
    // Set App1 menu and mount
    env.services.menu.setCurrentMenu(1);
    await mount(UserMenu, target, { env });
    assert.hasClass(target.querySelector(".o_user_menu"), "d-none");
    // remove the "d-none" class to make the menu visible before interacting with it
    target.querySelector(".o_user_menu").classList.remove("d-none");
    await click(target.querySelector("button.dropdown-toggle"));
    assert.containsOnce(target, ".dropdown-menu .dropdown-item");
    const item = target.querySelector(".dropdown-menu .dropdown-item");
    assert.strictEqual(item.textContent, "Add to Home Screen");
    await click(item);
    assert.verifySteps(['should call addHomeShortcut']);
});

QUnit.test("can execute the callback of addHomeShortcut on the HomeMenu", async (assert) => {
    assert.expect(4)
    patchWithCleanup(mobile.methods, {
        addHomeShortcut() {
            assert.step("shouldn't call addHomeShortcut");
        }
    });
    const mockNotification = (message) => {
        assert.step(`notification (${message})`);
        return () => {};
    }
    serviceRegistry.add("notification", makeFakeNotificationService(mockNotification));
    const env = await makeTestEnv();

    userMenuRegistry.add("web_mobile.shortcut", shortcutItem);
    await mount(UserMenu, target, { env });
    // remove the "d-none" class to make the menu visible before interacting with it
    target.querySelector(".o_user_menu").classList.remove("d-none");
    await click(target.querySelector("button.dropdown-toggle"));
    assert.containsOnce(target, ".dropdown-menu .dropdown-item");
    const item = target.querySelector(".dropdown-menu .dropdown-item");
    assert.strictEqual(item.textContent, "Add to Home Screen");
    await click(item);
    assert.verifySteps(["notification (No shortcut for Home Menu)"]);
});

QUnit.test("can execute the callback of switchAccount", async (assert) => {
    assert.expect(4)
    patchWithCleanup(mobile.methods, {
        switchAccount() {
            assert.step("should call switchAccount");
        }
    });
    const env = await makeTestEnv();

    userMenuRegistry.add("web_mobile.switch", switchAccountItem);
    await mount(UserMenu, target, { env });
    // remove the "d-none" class to make the menu visible before interacting with it
    target.querySelector(".o_user_menu").classList.remove("d-none");
    await click(target.querySelector("button.dropdown-toggle"));
    assert.containsOnce(target, ".dropdown-menu .dropdown-item");
    const item = target.querySelector(".dropdown-menu .dropdown-item");
    assert.strictEqual(item.textContent, "Switch/Add Account");
    await click(item);
    assert.verifySteps(["should call switchAccount"]);
});
