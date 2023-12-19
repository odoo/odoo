/** @odoo-module alias=@web/../tests/core/effects/effect_service_tests default=false */

import { notificationService } from "@web/core/notifications/notification_service";
import { registry } from "@web/core/registry";
import { effectService } from "@web/core/effects/effect_service";
import { makeTestEnv } from "../../helpers/mock_env";
import { makeFakeLocalizationService, patchUserWithCleanup } from "../../helpers/mock_services";
import { click, getFixture, mockTimeout, mount, nextTick } from "../../helpers/utils";

import { Component, markup, xml } from "@odoo/owl";
import { MainComponentsContainer } from "@web/core/main_components_container";

const serviceRegistry = registry.category("services");

let target;

async function makeParent() {
    const env = await makeTestEnv({ serviceRegistry });
    const parent = await mount(MainComponentsContainer, target, { env });
    return parent;
}

QUnit.module("Effect Service", (hooks) => {
    let effectParams;
    let execRegisteredTimeouts;
    hooks.beforeEach(() => {
        effectParams = {
            message: markup("<div>Congrats!</div>"),
        };

        execRegisteredTimeouts = mockTimeout().execRegisteredTimeouts;
        patchUserWithCleanup({ showEffect: true }); // enable effects

        serviceRegistry.add("effect", effectService);
        serviceRegistry.add("notification", notificationService);
        serviceRegistry.add("localization", makeFakeLocalizationService());

        target = getFixture();
    });

    QUnit.test("effect service displays a rainbowman by default", async function (assert) {
        const parent = await makeParent();
        parent.env.services.effect.add();
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(target, ".o_reward");
        assert.strictEqual(target.querySelector(".o_reward").innerText, "Well Done!");
    });

    QUnit.test("rainbowman effect with show_effect: false", async function (assert) {
        patchUserWithCleanup({ showEffect: false });

        const parent = await makeParent();
        parent.env.services.effect.add();
        await nextTick();
        execRegisteredTimeouts();

        assert.containsNone(target, ".o_reward");
        assert.containsOnce(target, ".o_notification");
    });

    QUnit.test("rendering a rainbowman destroy after animation", async function (assert) {
        const parent = await makeParent();
        parent.env.services.effect.add(effectParams);
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(target, ".o_reward");
        assert.containsOnce(target, ".o_reward_rainbow");
        assert.strictEqual(
            target.querySelector(".o_reward_msg_content").innerHTML,
            "<div>Congrats!</div>"
        );

        const ev = new AnimationEvent("animationend", { animationName: "reward-fading-reverse" });
        target.querySelector(".o_reward").dispatchEvent(ev);
        await nextTick();
        assert.containsNone(target, ".o_reward");
    });

    QUnit.test("rendering a rainbowman destroy on click", async function (assert) {
        const parent = await makeParent();

        parent.env.services.effect.add(effectParams);
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(target, ".o_reward");
        assert.containsOnce(target, ".o_reward_rainbow");

        await click(target);
        assert.containsNone(target, ".o_reward");
    });

    QUnit.test("rendering a rainbowman with an escaped message", async function (assert) {
        const parent = await makeParent();

        parent.env.services.effect.add(effectParams);
        await nextTick();
        execRegisteredTimeouts();

        assert.containsOnce(target, ".o_reward");
        assert.containsOnce(target, ".o_reward_rainbow");
        assert.strictEqual(target.querySelector(".o_reward_msg_content").textContent, "Congrats!");
    });

    QUnit.test("rendering a rainbowman with a custom component", async function (assert) {
        assert.expect(2);
        const props = { foo: "bar" };
        class Custom extends Component {
            static template = xml`<div class="custom">foo is <t t-esc="props.foo"/></div>`;
            static props = ["*"];
            setup() {
                assert.deepEqual(this.props, props, "should have received these props");
            }
        }

        const parent = await makeParent();
        parent.env.services.effect.add({ Component: Custom, props });
        await nextTick();
        execRegisteredTimeouts();
        assert.strictEqual(
            target.querySelector(".o_reward_msg_content").innerHTML,
            `<div class="custom">foo is bar</div>`
        );
    });
});
