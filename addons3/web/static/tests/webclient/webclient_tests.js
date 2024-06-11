/** @odoo-module **/

import { dialogService } from "@web/core/dialog/dialog_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { ormService } from "@web/core/orm_service";
import { popoverService } from "@web/core/popover/popover_service";
import { registry } from "@web/core/registry";
import { uiService } from "@web/core/ui/ui_service";
import { actionService } from "@web/webclient/actions/action_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { menuService } from "@web/webclient/menus/menu_service";
import { WebClient } from "@web/webclient/webclient";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { fakeTitleService } from "../helpers/mock_services";
import { destroy, getFixture, mount, patchWithCleanup, triggerEvent } from "../helpers/utils";

import { Component, xml } from "@odoo/owl";
const mainComponentRegistry = registry.category("main_components");
const serviceRegistry = registry.category("services");

let baseConfig;
let target;

QUnit.module("WebClient", {
    async beforeEach() {
        serviceRegistry
            .add("orm", ormService)
            .add("action", actionService)
            .add("dialog", dialogService)
            .add("hotkey", hotkeyService)
            .add("menu", menuService)
            .add("notification", notificationService)
            .add("popover", popoverService)
            .add("title", fakeTitleService)
            .add("ui", uiService);
        baseConfig = { activateMockServer: true };
        target = getFixture();
    },
});

QUnit.test("can be rendered", async (assert) => {
    assert.expect(1);
    const env = await makeTestEnv(baseConfig);
    await mount(WebClient, target, { env });
    assert.containsOnce(target, "header > nav.o_main_navbar");
});

QUnit.test("can render a main component", async (assert) => {
    assert.expect(1);
    class MyComponent extends Component {}
    MyComponent.template = xml`<span class="chocolate">MyComponent</span>`;
    clearRegistryWithCleanup(mainComponentRegistry);
    mainComponentRegistry.add("mycomponent", { Component: MyComponent });
    const env = await makeTestEnv(baseConfig);
    await mount(WebClient, target, { env });
    assert.containsOnce(target, ".chocolate");
});

QUnit.test("control-click propagation stopped on <a href/>", async (assert) => {
    assert.expect(8);

    patchWithCleanup(WebClient.prototype, {
        /** @param {MouseEvent} ev */
        onGlobalClick(ev) {
            super.onGlobalClick(ev);
            if (ev.ctrlKey) {
                assert.ok(
                    ev.defaultPrevented === false,
                    "the global click should not prevent the default behavior on ctrl-click an <a href/>"
                );
                // Necessary in order to prevent the test browser to open in new tab on ctrl-click
                ev.preventDefault();
            }
        },
    });

    class MyComponent extends Component {
        /** @param {MouseEvent} ev */
        onclick(ev) {
            assert.step(ev.ctrlKey ? "ctrl-click" : "click");
            // Necessary in order to prevent the test browser to open in new tab on ctrl-click
            ev.preventDefault();
        }
    }
    MyComponent.template = xml`<a href="#" class="MyComponent" t-on-click="onclick">Some link</a>`;
    let env = await makeTestEnv(baseConfig);

    // Mount the component as standalone and control-click the <a href/>
    const standaloneComponent = await mount(MyComponent, target, { env });
    assert.verifySteps([]);
    await triggerEvent(target.querySelector(".MyComponent"), "", "click", { ctrlKey: false });
    await triggerEvent(target.querySelector(".MyComponent"), "", "click", { ctrlKey: true });
    assert.verifySteps(["click", "ctrl-click"]);
    destroy(standaloneComponent);

    // Register the component as a main one, mount the webclient and control-click the <a href/>
    clearRegistryWithCleanup(mainComponentRegistry);
    mainComponentRegistry.add("mycomponent", { Component: MyComponent });
    env = await makeTestEnv(baseConfig);
    await mount(WebClient, target, { env });
    assert.verifySteps([]);
    await triggerEvent(target, ".MyComponent", "click", { ctrlKey: false });
    await triggerEvent(target, ".MyComponent", "click", { ctrlKey: true });
    assert.verifySteps(["click"]);
});
