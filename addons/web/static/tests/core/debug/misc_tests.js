/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { effectService } from "@web/core/effects/effect_service";
import { userService } from "@web/core/user_service";
import { commandService } from "@web/core/commands/command_service";
import { makeTestEnv } from "../../helpers/mock_env";
import {
    getFixture,
    mount,
    patchWithCleanup,
    mockTimeout,
    nextTick,
    triggerHotkey,
} from "../../helpers/utils";

const { Component, xml } = owl;


const serviceRegistry = registry.category("services");
const mainComponentRegistry = registry.category("main_components");


let target;
QUnit.module("Effect Service", (hooks) => {
    let execRegisteredTimeouts;
    hooks.beforeEach(() => {

        execRegisteredTimeouts = mockTimeout();
        patchWithCleanup(session, { show_effect: true }); // enable effects

        serviceRegistry.add("user", userService);
        serviceRegistry.add("effect", effectService);
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("command", commandService);

        target = getFixture();
    });

    QUnit.test("FP request", async (assert) => {
        assert.expect(4);
        class Parent extends Component {
            setup() {
                this.EffectContainer = mainComponentRegistry.get("EffectContainer");
                this.NotificationContainer = mainComponentRegistry.get("NotificationContainer");
            }
        }
        Parent.template = xml`
            <div>
              <t t-component="EffectContainer.Component" t-props="EffectContainer.props" />
              <t t-component="NotificationContainer.Component" t-props="NotificationContainer.props" />
            </div>
          `;

        const env = await makeTestEnv({ serviceRegistry });
        await mount(Parent, target, { env });

        triggerHotkey(`control+ArrowUp`);
        triggerHotkey(`control+ArrowUp`);
        triggerHotkey(`control+ArrowDown`);
        triggerHotkey(`control+ArrowDown`);
        triggerHotkey(`control+ArrowLeft`);
        triggerHotkey(`control+ArrowRight`);
        triggerHotkey(`control+ArrowLeft`);
        triggerHotkey(`control+ArrowRight`);
        triggerHotkey(`control+b`);

        await nextTick();
        execRegisteredTimeouts();
        assert.containsNone(target, ".o_reward");
        assert.containsNone(target, ".o_reward_rainbow");

        triggerHotkey(`control+a`);
        await nextTick();
        execRegisteredTimeouts();
        assert.containsOnce(target, ".o_reward");
        assert.containsOnce(target, ".o_reward_rainbow");
    });
})
