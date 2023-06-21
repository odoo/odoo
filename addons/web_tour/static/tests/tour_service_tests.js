/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { MacroEngine } from "@web/core/macro";
import { registry } from "@web/core/registry";
import { tourService } from "@web_tour/tour_service/tour_service";
import { rpcService } from "@web/core/network/rpc_service";
import { userService } from "@web/core/user_service";
import { ormService } from "@web/core/orm_service";
import { notificationService } from "@web/core/notifications/notification_service";
import { effectService } from "@web/core/effects/effect_service";
import { registerCleanup } from "@web/../tests/helpers/cleanup";
import {
    getFixture,
    mount,
    mockTimeout,
    editInput,
    click,
    triggerEvent,
    nextTick,
    patchWithCleanup,
} from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { Component, useState, xml } from "@odoo/owl";
import { session } from "@web/session";

let target, mock;

QUnit.module("Tour service", (hooks) => {
    QUnit.module("tour_service");

    let tourRegistry;

    class Counter extends Component {
        static template = xml/*html*/ `
            <div class="counter">
                <div class="interval">
                    <input type="number" t-model.number="state.interval" />
                </div>
                <div class="counter">
                    <span class="value" t-esc="state.value" />
                    <button class="inc" t-on-click="onIncrement">+</button>
                </div>
            </div>
        `;
        setup() {
            this.state = useState({ interval: 1, value: 0 });
        }
        onIncrement() {
            this.state.value += this.state.interval;
        }
    }

    hooks.beforeEach(() => {
        target = getFixture();
        mock = mockTimeout();
        tourRegistry = registry.category("web_tour.tours");
        delete registry.subRegistries["web_tour.tours"];
        let macroEngines = [];
        patchWithCleanup(MacroEngine.prototype, {
            start() {
                super.start(...arguments);
                macroEngines.push(this);
            },
        });
        registerCleanup(() => {
            macroEngines.forEach((e) => e.stop());
            macroEngines = [];
        });
        registry
            .category("services")
            .add("rpc", rpcService)
            .add("user", userService)
            .add("orm", ormService)
            .add("notification", notificationService)
            .add("effect", effectService)
            .add("tour_service", tourService);
        patchWithCleanup(browser.console, {
            // prevent form logging "tour successful" which would end the qunit suite test
            log: () => {},
        });
    });

    hooks.afterEach(() => {
        registry.subRegistries["web_tour.tours"] = tourRegistry;
    });

    QUnit.test("Tours sequence", async function (assert) {
        registry
            .category("web_tour.tours")
            .add("Tour 1", {
                sequence: 10,
                steps: () => [{ trigger: ".anchor" }],
            })
            .add("Tour 2", { steps: () => [{ trigger: ".anchor" }] })
            .add("Tour 3", {
                sequence: 5,
                steps: () => [{ trigger: ".anchor", content: "Oui" }],
            });
        const env = await makeTestEnv({});
        const sortedTours = env.services.tour_service.getSortedTours();
        assert.strictEqual(sortedTours[0].name, "Tour 3");
    });

    QUnit.test("override existing tour by using saveAs", async function (assert) {
        registry
            .category("web_tour.tours")
            .add("Tour 1", {
                steps: () => [{ trigger: "#1" }],
                saveAs: "homepage",
            })
            .add("Tour 2", {
                steps: () => [{ trigger: "#2" }],
                saveAs: "homepage",
            });
        const env = await makeTestEnv({});
        const sortedTours = env.services.tour_service.getSortedTours();
        assert.strictEqual(sortedTours.length, 1);
        assert.deepEqual(sortedTours[0].steps, [{ shadow_dom: undefined, trigger: "#2" }]);
        assert.deepEqual(sortedTours[0].name, "homepage");
    });

    QUnit.test("points to next step", async function (assert) {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [
                {
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Root extends Component {
            static components = { OverlayContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        await mock.advanceTime(800);
        assert.containsOnce(document.body, ".o_tour_pointer");
        await click(target, "button.inc");
        assert.containsNone(document.body, ".o_tour_pointer");
        assert.strictEqual(target.querySelector("span.value").textContent, "1");
    });

    QUnit.test("next step with new anchor at same position", async (assert) => {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [{ trigger: "button.foo" }, { trigger: "button.bar" }],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Dummy extends Component {
            state = useState({ bool: true });
            static template = xml/*html*/ `
                <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
                <button class="bar w-100" t-if="!state.bool">Bar</button>
            `;
        }
        class Root extends Component {
            static components = { OverlayContainer, Dummy };
            static template = xml/*html*/ `
                <t>
                    <Dummy />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        await mock.advanceTime(100);
        assert.containsOnce(document.body, ".o_tour_pointer");

        // check position of the pointer relative to the foo button
        let pointerRect = document.body.querySelector(".o_tour_pointer").getBoundingClientRect();
        let buttonRect = document.body.querySelector("button.foo").getBoundingClientRect();
        const leftValue1 = pointerRect.left - buttonRect.left;
        const bottomValue1 = pointerRect.bottom - buttonRect.bottom;
        assert.ok(leftValue1 !== 0);
        assert.ok(bottomValue1 !== 0);

        await click(target, "button.foo");
        await mock.advanceTime(100);
        assert.containsOnce(document.body, ".o_tour_pointer");

        // check position of the pointer relative to the bar button
        pointerRect = document.body.querySelector(".o_tour_pointer").getBoundingClientRect();
        buttonRect = document.body.querySelector("button.bar").getBoundingClientRect();
        const leftValue2 = pointerRect.left - buttonRect.left;
        const bottomValue2 = pointerRect.bottom - buttonRect.bottom;
        assert.strictEqual(bottomValue1, bottomValue2);
        assert.strictEqual(leftValue1, leftValue2);
    });

    QUnit.test("scroller pointer to reach next step", async function (assert) {
        patchWithCleanup(Element.prototype, {
            scrollIntoView(options) {
                super.scrollIntoView({ ...options, behavior: "instant" });
            },
        });

        // The fixture should be shown for this test
        target.style.position = "fixed";
        target.style.top = "200px";
        target.style.left = "50px";

        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [{ trigger: "button.inc", content: "Click to increment" }],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Root extends Component {
            static components = { OverlayContainer, Counter };
            static template = xml/*html*/ `
                <div class="scrollable-parent" style="overflow-y: scroll; height: 150px;">
                    <div class="top-filler" style="height: 300px" />
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                    <div class="bottom-filler" style="height: 300px" />
                </div>
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        await mock.advanceTime(100); // awaits the macro engine

        // Even if this seems weird, it should show the initial pointer.
        // This is due to the fact the intersection observer has just been started and
        // the pointer did not have the observations yet when the pointTo method was called.
        // This is a bit tricky to change for now because the synchronism of the pointTo method
        // is what permits to avoid multiple pointer to be shown at the same time
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(
            document.body.querySelector(".o_tour_pointer").textContent,
            "Click to increment"
        );

        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        // now the scroller pointer should be shown
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(
            document.body.querySelector(".o_tour_pointer").textContent,
            "Scroll down to reach the next step."
        );

        // awaiting the click here permits to the intersection observer to update
        await click(document.body, ".o_tour_pointer");
        assert.containsNone(document.body, ".o_tour_pointer");
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(
            document.body.querySelector(".o_tour_pointer").textContent,
            "Click to increment"
        );

        document.querySelector(".scrollable-parent").scrollTop = 1000;
        await nextTick(); // awaits the intersection observer to update after the scroll
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(
            document.body.querySelector(".o_tour_pointer").textContent,
            "Scroll up to reach the next step."
        );

        // awaiting the click here permits to the intersection observer to update
        await click(document.body, ".o_tour_pointer");
        assert.containsNone(document.body, ".o_tour_pointer");
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(
            document.body.querySelector(".o_tour_pointer").textContent,
            "Click to increment"
        );
    });

    QUnit.test("scrolling to next step should update the pointer's height", async (assert) => {
        patchWithCleanup(Element.prototype, {
            scrollIntoView(options) {
                super.scrollIntoView({ ...options, behavior: "instant" });
            },
        });

        // The fixture should be shown for this test
        target.style.position = "fixed";
        target.style.top = "200px";
        target.style.left = "50px";

        const stepContent = "Click this pretty button to increment this magnificent counter !";
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [
                {
                    trigger: "button.inc",
                    content: stepContent,
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Root extends Component {
            static components = { OverlayContainer, Counter };
            static template = xml/*html*/ `
                <div class="scrollable-parent" style="overflow-y: scroll; height: 150px;">
                    <Counter />
                    <div class="bottom-filler" style="height: 300px" />
                </div>
                <OverlayContainer t-props="props.overlayContainerProps" />
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        await mock.advanceTime(100); // awaits the macro engine
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(document.body.querySelector(".o_tour_pointer").textContent, stepContent);

        const pointer = document.body.querySelector(".o_tour_pointer");
        assert.doesNotHaveClass(pointer, "o_open");
        assert.strictEqual(pointer.style.height, "28px");
        assert.strictEqual(pointer.style.width, "28px");

        await triggerEvent(document.body, ".o_tour_pointer", "mouseenter");
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        assert.hasClass(pointer, "o_open");
        const firstOpenHeight = pointer.style.height;
        const firstOpenWidth = pointer.style.width;

        await triggerEvent(document.body, ".o_tour_pointer", "mouseleave");
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        assert.doesNotHaveClass(pointer, "o_open");

        document.querySelector(".scrollable-parent").scrollTop = 1000;
        await nextTick(); // awaits the intersection observer to update after the scroll
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        // now the scroller pointer should be shown
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(
            document.body.querySelector(".o_tour_pointer").textContent,
            "Scroll up to reach the next step."
        );

        document.querySelector(".scrollable-parent").scrollTop = 0;
        await nextTick(); // awaits the intersection observer to update after the scroll
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        // now the true step pointer should be shown again
        assert.containsOnce(document.body, ".o_tour_pointer");
        assert.equal(document.body.querySelector(".o_tour_pointer").textContent, stepContent);

        await triggerEvent(document.body, ".o_tour_pointer", "mouseenter");
        await mock.advanceTime(100); // awaits for the macro engine next check cycle
        assert.hasClass(pointer, "o_open");
        const secondOpenHeight = pointer.style.height;
        const secondOpenWidth = pointer.style.width;
        assert.strictEqual(firstOpenHeight, secondOpenHeight);
        assert.strictEqual(firstOpenWidth, secondOpenWidth);
    });

    QUnit.test("perform edit on next step", async function (assert) {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [
                {
                    trigger: ".interval input",
                },
                {
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Root extends Component {
            static components = { OverlayContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        await mock.advanceTime(750);
        assert.containsOnce(document.body, ".o_tour_pointer");
        await editInput(target, ".interval input", "5");
        assert.containsNone(document.body, ".o_tour_pointer");
        await mock.advanceTime(750);
        assert.containsOnce(document.body, ".o_tour_pointer");
        await click(target, "button.inc");
        assert.strictEqual(target.querySelector(".counter .value").textContent, "5");
    });

    QUnit.test("trigger an event when a step is consummed", async function (assert) {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [{ trigger: ".interval input" }],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Root extends Component {
            static components = { OverlayContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        env.services.tour_service.bus.addEventListener("STEP-CONSUMMED", ({ detail }) => {
            assert.step(`Tour ${detail.tour.name}, step ${detail.step.trigger}`);
        });
        await mock.advanceTime(750);
        await editInput(target, ".interval input", "5");
        await mock.advanceTime(750);
        assert.verifySteps(["Tour tour1, step .interval input"]);
    });

    QUnit.test("should show only 1 pointer at a time", async function (assert) {
        const storage = new Map();
        patchWithCleanup(browser.localStorage, {
            getItem: (key) => storage.get(key),
            setItem: (key, value) => storage.set(key, value),
            removeItem: (key) => storage.delete(key),
            tour__tour1__sequence: 0,
            tour__tour2__sequence: 0,
        });

        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [
                {
                    trigger: ".interval input",
                },
            ],
        });
        registry.category("web_tour.tours").add("tour2", {
            sequence: 10,
            steps: () => [
                {
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Root extends Component {
            static components = { OverlayContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        env.services.tour_service.startTour("tour2", { mode: "manual" });
        await mock.advanceTime(750);
        assert.containsOnce(document.body, ".o_tour_pointer");
        await editInput(target, ".interval input", "5");
        assert.containsNone(document.body, ".o_tour_pointer");
        await mock.advanceTime(750);
        assert.containsOnce(document.body, ".o_tour_pointer");
    });

    QUnit.test("hovering to the anchor element should show the content", async function (assert) {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: () => [
                {
                    content: "content",
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: OverlayContainer, props: overlayContainerProps } = registry
            .category("main_components")
            .get("OverlayContainer");

        class Root extends Component {
            static components = { OverlayContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { overlayContainerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        await mock.advanceTime(750);
        assert.containsOnce(target, ".o_tour_pointer");
        triggerEvent(target, "button.inc", "mouseenter");
        await nextTick();
        assert.containsOnce(target, ".o_tour_pointer_content:not(.invisible)");
        assert.strictEqual(
            target.querySelector(".o_tour_pointer_content:not(.invisible)").textContent,
            "content"
        );
        triggerEvent(target, "button.inc", "mouseleave");
        await nextTick();
        assert.containsOnce(target, ".o_tour_pointer_content.invisible");
    });

    QUnit.test(
        "registering non-test tour after service is started auto-starts the tour",
        async function (assert) {
            patchWithCleanup(session, { tour_disable: false });
            const env = await makeTestEnv({});

            const { Component: OverlayContainer, props: overlayContainerProps } = registry
                .category("main_components")
                .get("OverlayContainer");

            class Root extends Component {
                static components = { OverlayContainer, Counter };
                static template = xml/*html*/ `
                <t>
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
            }

            await mount(Root, target, { env, props: { overlayContainerProps } });
            assert.containsNone(target, ".o_tour_pointer");
            registry.category("web_tour.tours").add("tour1", {
                steps: () => [
                    {
                        content: "content",
                        trigger: "button.inc",
                    },
                ],
            });
            await mock.advanceTime(750);
            await nextTick();
            assert.containsOnce(target, ".o_tour_pointer");
        }
    );

    QUnit.test(
        "registering test tour after service is started doesn't auto-start the tour",
        async function (assert) {
            patchWithCleanup(session, { tour_disable: false });
            const env = await makeTestEnv({});

            const { Component: OverlayContainer, props: overlayContainerProps } = registry
                .category("main_components")
                .get("OverlayContainer");

            class Root extends Component {
                static components = { OverlayContainer, Counter };
                static template = xml/*html*/ `
                <t>
                    <Counter />
                    <OverlayContainer t-props="props.overlayContainerProps" />
                </t>
            `;
            }

            await mount(Root, target, { env, props: { overlayContainerProps } });
            assert.containsNone(target, ".o_tour_pointer");
            registry.category("web_tour.tours").add("tour1", {
                test: true,
                steps: () => [
                    {
                        content: "content",
                        trigger: "button.inc",
                    },
                ],
            });
            await mock.advanceTime(750);
            await nextTick();
            assert.containsNone(target, ".o_tour_pointer");
        }
    );
});
