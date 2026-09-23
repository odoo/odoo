// @ts-check

import { beforeEach, expect, onError, test } from "@odoo/hoot";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, onWillStart, useState, xml } from "@odoo/owl";
import {
    clearRegistry,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { MainComponentsContainer } from "@web/ui/main_components_container";

const mainComponentsRegistry = registry.category("main_components");

beforeEach(async () => {
    clearRegistry(mainComponentsRegistry);
});

test("simple rendering", async () => {
    class MainComponentA extends Component {
        static template = xml`<span>MainComponentA</span>`;
        static props = ["*"];
    }

    class MainComponentB extends Component {
        static template = xml`<span>MainComponentB</span>`;
        static props = ["*"];
    }

    mainComponentsRegistry.add("MainComponentA", {
        Component: MainComponentA,
        props: {},
    });
    mainComponentsRegistry.add("MainComponentB", {
        Component: MainComponentB,
        props: {},
    });
    await mountWithCleanup(MainComponentsContainer);
    expect("div.o-main-components-container").toHaveCount(1);
    expect(".o-main-components-container > span:first-child").toHaveText(
        "MainComponentA",
    );
    expect(".o-main-components-container > span:nth-child(2)").toHaveText(
        "MainComponentB",
    );
});

test("unmounts erroring main component", async () => {
    expect.assertions(7);
    expect.errors(1);
    onError((/** @type {any} */ error) => {
        expect.step(error.reason.message);
        expect.step(error.reason.cause.message);
    });
    /** @type {any} */
    let compA;
    class MainComponentA extends Component {
        static template = xml`<span><t t-if="this.state.shouldThrow" t-out="this.error"/>MainComponentA</span>`;
        static props = ["*"];
        setup() {
            compA = this;
            this.state = useState({ shouldThrow: false });
        }
        get error() {
            throw new Error("BOOM");
        }
    }

    class MainComponentB extends Component {
        static template = xml`<span>MainComponentB</span>`;
        static props = ["*"];
    }

    mainComponentsRegistry.add("MainComponentA", {
        Component: MainComponentA,
        props: {},
    });
    mainComponentsRegistry.add("MainComponentB", {
        Component: MainComponentB,
        props: {},
    });
    await mountWithCleanup(MainComponentsContainer);
    expect("div.o-main-components-container").toHaveCount(1);
    expect(".o-main-components-container > span:first-child").toHaveText(
        "MainComponentA",
    );
    expect(".o-main-components-container > span:nth-child(2)").toHaveText(
        "MainComponentB",
    );
    compA.state.shouldThrow = true;
    await animationFrame();
    expect.verifySteps([
        'An error occured in the owl lifecycle (see this Error\'s "cause" property)',
        "BOOM",
    ]);
    expect.verifyErrors(["BOOM"]);

    expect(".o-main-components-container > span").toHaveCount(1);
    expect(".o-main-components-container > span").toHaveText("MainComponentB");
});

test("unmounts erroring main component: variation", async () => {
    expect.assertions(7);
    expect.errors(1);
    onError((/** @type {any} */ error) => {
        expect.step(error.reason.message);
        expect.step(error.reason.cause.message);
    });
    class MainComponentA extends Component {
        static template = xml`<span>MainComponentA</span>`;
        static props = ["*"];
    }

    /** @type {any} */
    let compB;
    class MainComponentB extends Component {
        static template = xml`<span><t t-if="this.state.shouldThrow" t-out="this.error"/>MainComponentB</span>`;
        static props = ["*"];
        setup() {
            compB = this;
            this.state = useState({ shouldThrow: false });
        }
        get error() {
            throw new Error("BOOM");
        }
    }

    mainComponentsRegistry.add("MainComponentA", {
        Component: MainComponentA,
        props: {},
    });
    mainComponentsRegistry.add("MainComponentB", {
        Component: MainComponentB,
        props: {},
    });
    await mountWithCleanup(MainComponentsContainer);
    expect("div.o-main-components-container").toHaveCount(1);
    expect(".o-main-components-container > span:first-child").toHaveText(
        "MainComponentA",
    );
    expect(".o-main-components-container > span:nth-child(2)").toHaveText(
        "MainComponentB",
    );
    compB.state.shouldThrow = true;
    await animationFrame();
    expect.verifySteps([
        'An error occured in the owl lifecycle (see this Error\'s "cause" property)',
        "BOOM",
    ]);
    expect.verifyErrors(["BOOM"]);
    expect(".o-main-components-container > span").toHaveCount(1);
    expect(".o-main-components-container > span").toHaveText("MainComponentA");
});

test("MainComponentsContainer re-renders when the registry changes", async () => {
    await mountWithCleanup(MainComponentsContainer);

    expect(".myMainComponent").toHaveCount(0);
    class MyMainComponent extends Component {
        static template = xml`<div class="myMainComponent" />`;
        static props = ["*"];
    }
    mainComponentsRegistry.add("myMainComponent", { Component: MyMainComponent });
    await animationFrame();
    expect(".myMainComponent").toHaveCount(1);
});

test("Should be possible to add a new component when MainComponentContainer is not mounted yet", async () => {
    const defer = new Deferred();
    patchWithCleanup(MainComponentsContainer.prototype, {
        setup() {
            super.setup();
            onWillStart(async () => {
                await defer;
            });
        },
    });
    const mounted = mountWithCleanup(MainComponentsContainer);
    class MyMainComponent extends Component {
        static template = xml`<div class="myMainComponent" />`;
        static props = ["*"];
    }
    mainComponentsRegistry.add("myMainComponent", { Component: MyMainComponent });
    defer.resolve();
    await mounted;
    await animationFrame();
    expect(".myMainComponent").toHaveCount(1);
});

test("an error from an entry no longer in the snapshot removes nothing", async () => {
    expect.errors(1);

    class MainComponentA extends Component {
        static template = xml`<span>A</span>`;
        static props = ["*"];
    }
    class MainComponentB extends Component {
        static template = xml`<span>B</span>`;
        static props = ["*"];
    }
    mainComponentsRegistry.add("A", { Component: MainComponentA, props: {} });
    mainComponentsRegistry.add("B", { Component: MainComponentB, props: {} });
    const container = await mountWithCleanup(MainComponentsContainer);
    const before = container.Components.entries.map((e) => e[0]);

    container.handleComponentError(
        new Error("BOOM"),
        /** @type {any} */ (["ghost", { Component: MainComponentA, props: {} }]),
    );
    await animationFrame();

    expect(container.Components.entries.map((e) => e[0])).toEqual(before);
    expect.verifyErrors(["BOOM"]);
});

test("a crashing main component is dropped from the registry too", async () => {
    expect.errors(1);

    class Boom extends Component {
        static props = {};
        static template = xml`<div class="boom"/>`;
        setup() {
            throw new Error("boom");
        }
    }
    mainComponentsRegistry.add("Boom", { Component: Boom });
    await mountWithCleanup(MainComponentsContainer);
    await animationFrame();
    expect(".boom").toHaveCount(0);
    expect(mainComponentsRegistry.contains("Boom")).toBe(false);
    expect.verifyErrors(["boom"]);
});
