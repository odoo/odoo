/** @odoo-module **/

import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { effectService } from "@web/core/effects/effect_service";
import { userService } from "@web/core/user_service";
import { session } from "@web/session";
import { makeTestEnv } from "../../helpers/mock_env";
import { makeFakeLocalizationService } from "../../helpers/mock_services";
import {
    click,
    getFixture,
    mockTimeout,
    mount,
    nextTick,
    patchWithCleanup,
} from "../../helpers/utils";

const { Component, xml } = owl;
const serviceRegistry = registry.category("services");
const mainComponentRegistry = registry.category("main_components");

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

async function makeParent() {
    const env = await makeTestEnv({ serviceRegistry });
    const target = getFixture();
    const parent = await mount(Parent, { env, target });
    return parent;
}

QUnit.module("Effect Service", (hooks) => {
    let effectParams;
    let execRegisteredTimeouts;
    hooks.beforeEach(() => {
        effectParams = {
            message: owl.markup("<div>Congrats!</div>"),
        };

        execRegisteredTimeouts = mockTimeout();
        patchWithCleanup(session, { show_effect: true }); // enable effects

        serviceRegistry.add("user", userService);
        serviceRegistry.add("effect", effectService);
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("localization", makeFakeLocalizationService());
    });

    QUnit.test("effect service displays a rainbowman by default", async function (assert) {
        const parent = await makeParent();
        parent.env.services.effect.add();
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(parent.el, ".o_reward");
        assert.strictEqual(parent.el.querySelector(".o_reward").innerText, "Well Done!");
    });

    QUnit.test("rainbowman effect with show_effect: false", async function (assert) {
        patchWithCleanup(session, { show_effect: false });

        const parent = await makeParent();
        parent.env.services.effect.add();
        await nextTick();
        execRegisteredTimeouts();

        assert.containsNone(parent.el, ".o_reward");
        assert.containsOnce(parent.el, ".o_notification");
    });

    QUnit.test("rendering a rainbowman destroy after animation", async function (assert) {
        const parent = await makeParent();
        parent.env.services.effect.add(effectParams);
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(parent, ".o_reward");
        assert.containsOnce(parent, ".o_reward_rainbow");
        assert.strictEqual(
            parent.el.querySelector(".o_reward_msg_content").innerHTML,
            "<div>Congrats!</div>"
        );

        const ev = new AnimationEvent("animationend", { animationName: "reward-fading-reverse" });
        parent.el.querySelector(".o_reward").dispatchEvent(ev);
        await nextTick();
        assert.containsNone(parent, ".o_reward");
    });

    QUnit.test("rendering a rainbowman destroy on click", async function (assert) {
        const parent = await makeParent();

        parent.env.services.effect.add(effectParams);
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(parent.el, ".o_reward");
        assert.containsOnce(parent.el, ".o_reward_rainbow");

        await click(parent.el);
        assert.containsNone(parent, ".o_reward");
    });

    QUnit.test("rendering a rainbowman with an escaped message", async function (assert) {
        const parent = await makeParent();

        parent.env.services.effect.add(effectParams);
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(parent.el, ".o_reward");
        assert.containsOnce(parent.el, ".o_reward_rainbow");
        assert.strictEqual(
            parent.el.querySelector(".o_reward_msg_content").textContent,
            "Congrats!"
        );
    });

    QUnit.test("rendering a rainbowman with a custom component", async function (assert) {
        assert.expect(2);
        const props = { foo: "bar" };
        class Custom extends Component {
            setup() {
                assert.deepEqual(this.props, props, "should have received these props");
            }
        }
        Custom.template = xml`<div class="custom">foo is <t t-esc="props.foo"/></div>`;

        const parent = await makeParent();
        parent.env.services.effect.add({ Component: Custom, props });
        await nextTick();
        execRegisteredTimeouts();
        assert.strictEqual(
            parent.el.querySelector(".o_reward_msg_content").innerHTML,
            `<div class="custom">foo is bar</div>`
        );
    });
});
