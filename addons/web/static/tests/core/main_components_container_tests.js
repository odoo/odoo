/** @odoo-module **/
import { MainComponentsContainer } from "@web/core/main_components_container";
import { registry } from "@web/core/registry";
import { clearRegistryWithCleanup, makeTestEnv } from "../helpers/mock_env";
import { patch, unpatch } from "@web/core/utils/patch";
import { getFixture, nextTick } from "../helpers/utils";

const { mount, Component } = owl;
const { useState } = owl.hooks;
const { xml } = owl.tags;
const mainComponentsRegistry = registry.category("main_components");
let container;
let target;

QUnit.module("Components", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        clearRegistryWithCleanup(mainComponentsRegistry);
    });
    hooks.afterEach(() => {
        if (container) {
            container.unmount();
            container = undefined;
        }
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
        container = await mount(MainComponentsContainer, { env, target, props: {} });
        assert.equal(
            container.el.outerHTML,
            "<div><span>MainComponentA</span><span>MainComponentB</span></div>"
        );
    });

    QUnit.test("unmounts erroring main component", async function (assert) {
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
        container = await mount(MainComponentsContainer, { env, target, props: {} });
        assert.equal(
            container.el.outerHTML,
            "<div><span>MainComponentA</span><span>MainComponentB</span></div>"
        );

        const handler = (ev) => {
            assert.step(ev.reason.message);
            // need to preventDefault to remove error from console (so python test pass)
            ev.preventDefault();
        };
        window.addEventListener("unhandledrejection", handler);
        patch(QUnit, "MainComponentsContainer QUnit patch", {
            onUnhandledRejection: () => {},
        });
        compA.state.shouldThrow = true;
        await nextTick();
        window.removeEventListener("unhandledrejection", handler);
        // unpatch QUnit asap so any other errors can be caught by it
        unpatch(QUnit, "MainComponentsContainer QUnit patch");
        assert.verifySteps(["BOOM"]);

        assert.equal(container.el.outerHTML, "<div><span>MainComponentB</span></div>");
    });

    QUnit.test("unmounts erroring main component: variation", async function (assert) {
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
        container = await mount(MainComponentsContainer, { env, target, props: {} });
        assert.equal(
            container.el.outerHTML,
            "<div><span>MainComponentA</span><span>MainComponentB</span></div>"
        );

        const handler = (ev) => {
            assert.step(ev.reason.message);
            // need to preventDefault to remove error from console (so python test pass)
            ev.preventDefault();
        };
        window.addEventListener("unhandledrejection", handler);
        patch(QUnit, "MainComponentsContainer QUnit patch", {
            onUnhandledRejection: () => {},
        });
        compB.state.shouldThrow = true;
        await nextTick();
        window.removeEventListener("unhandledrejection", handler);
        // unpatch QUnit asap so any other errors can be caught by it
        unpatch(QUnit, "MainComponentsContainer QUnit patch");
        assert.verifySteps(["BOOM"]);

        assert.equal(container.el.outerHTML, "<div><span>MainComponentA</span></div>");
    });
});
