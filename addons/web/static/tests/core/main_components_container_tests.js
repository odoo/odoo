/** @odoo-module **/
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { getFixture, mount, nextTick } from "../helpers/utils";

import { Component, useState, xml } from "@odoo/owl";
import { registerCleanup } from "../helpers/cleanup";
const mainComponentsRegistry = registry.category("main_components");

let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        clearRegistryWithCleanup(mainComponentsRegistry);
    });

    QUnit.module("MainComponentsContainer");

    QUnit.test("simple rendering", async function (assert) {
        const env = await makeTestEnv();

        class MainComponentA extends Component {}
        MainComponentA.template = xml`<span>MainComponentA</span>`;

        class MainComponentB extends Component {}
        MainComponentB.template = xml`<span>MainComponentB</span>`;

        mainComponentsRegistry.add("MainComponentA", { Component: MainComponentA, props: {} });
        mainComponentsRegistry.add("MainComponentB", { Component: MainComponentB, props: {} });
        await mount(MainComponentsContainer, target, { env, props: {} });
        assert.containsOnce(target, "div.o-main-components-container");
        assert.equal(
            target.querySelector(".o-main-components-container").innerHTML,
            "<span>MainComponentA</span><span>MainComponentB</span>"
        );
    });

    QUnit.test("unmounts erroring main component", async function (assert) {
        assert.expectErrors();
        const env = await makeTestEnv();

        let compA;
        class MainComponentA extends Component {
            setup() {
                compA = this;
                this.state = useState({ shouldThrow: false });
            }
            get error() {
                throw new Error("BOOM");
            }
        }
        MainComponentA.template = xml`<span><t t-if="state.shouldThrow" t-esc="error"/>MainComponentA</span>`;

        class MainComponentB extends Component {}
        MainComponentB.template = xml`<span>MainComponentB</span>`;

        mainComponentsRegistry.add("MainComponentA", { Component: MainComponentA, props: {} });
        mainComponentsRegistry.add("MainComponentB", { Component: MainComponentB, props: {} });
        await mount(MainComponentsContainer, target, { env, props: {} });
        assert.containsOnce(target, "div.o-main-components-container");
        assert.equal(
            target.querySelector(".o-main-components-container").innerHTML,
            "<span>MainComponentA</span><span>MainComponentB</span>"
        );

        const handler = (ev) => {
            assert.step(ev.reason.message);
            assert.step(ev.reason.cause.message);
        };
        window.addEventListener("unhandledrejection", handler);
        registerCleanup(() => {
            window.removeEventListener("unhandledrejection", handler);
        });
        compA.state.shouldThrow = true;
        await nextTick();
        assert.verifySteps([
            'An error occured in the owl lifecycle (see this Error\'s "cause" property)',
            "BOOM",
        ]);
        assert.verifyErrors(["BOOM"]);

        assert.equal(
            target.querySelector(".o-main-components-container").innerHTML,
            "<span>MainComponentB</span>"
        );
    });

    QUnit.test("unmounts erroring main component: variation", async function (assert) {
        assert.expectErrors();

        const env = await makeTestEnv();

        class MainComponentA extends Component {}
        MainComponentA.template = xml`<span>MainComponentA</span>`;

        let compB;
        class MainComponentB extends Component {
            setup() {
                compB = this;
                this.state = useState({ shouldThrow: false });
            }
            get error() {
                throw new Error("BOOM");
            }
        }
        MainComponentB.template = xml`<span><t t-if="state.shouldThrow" t-esc="error"/>MainComponentB</span>`;

        mainComponentsRegistry.add("MainComponentA", { Component: MainComponentA, props: {} });
        mainComponentsRegistry.add("MainComponentB", { Component: MainComponentB, props: {} });
        await mount(MainComponentsContainer, target, { env, props: {} });
        assert.containsOnce(target, "div.o-main-components-container");
        assert.equal(
            target.querySelector(".o-main-components-container").innerHTML,
            "<span>MainComponentA</span><span>MainComponentB</span>"
        );

        const handler = (ev) => {
            assert.step(ev.reason.message);
            assert.step(ev.reason.cause.message);
        };
        window.addEventListener("unhandledrejection", handler);
        registerCleanup(() => {
            window.removeEventListener("unhandledrejection", handler);
        });
        compB.state.shouldThrow = true;
        await nextTick();
        assert.verifySteps([
            'An error occured in the owl lifecycle (see this Error\'s "cause" property)',
            "BOOM",
        ]);
        assert.verifyErrors(["BOOM"]);
        assert.equal(
            target.querySelector(".o-main-components-container").innerHTML,
            "<span>MainComponentA</span>"
        );
    });

    QUnit.test("MainComponentsContainer re-renders when the registry changes", async (assert) => {
        const env = await makeTestEnv();
        await mount(MainComponentsContainer, target, { env, props: {} });

        assert.containsNone(target, ".myMainComponent");
        class MyMainComponent extends Component {}
        MyMainComponent.template = xml`<div class="myMainComponent" />`;
        mainComponentsRegistry.add("myMainComponent", { Component: MyMainComponent });
        await nextTick();
        assert.containsOnce(target, ".myMainComponent");
    });
});
