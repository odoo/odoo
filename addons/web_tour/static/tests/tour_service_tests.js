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
                this._super(...arguments);
                macroEngines.push(this);
            }
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
            log: () => {}
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
                steps: [{ trigger: ".anchor" }],
            })
            .add("Tour 2", { steps: [{ trigger: ".anchor" }] })
            .add("Tour 3", {
                sequence: 5,
                steps: [{ trigger: ".anchor", content: "Oui" }],
            });
        const env = await makeTestEnv({});
        const sortedTours = env.services.tour_service.getSortedTours();
        assert.strictEqual(sortedTours[0].name, "Tour 3");
    });

    QUnit.test("points to next step", async function (assert) {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: [
                {
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: TourPointerContainer, props: tourPointerProps } = registry
            .category("main_components")
            .get("TourPointerContainer");

        class Root extends Component {
            static components = { TourPointerContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <TourPointerContainer t-props="props.tourPointerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { tourPointerProps } });
        env.services.tour_service.startTour("tour1", { mode: "manual" });
        await mock.advanceTime(800);
        assert.containsOnce(document.body, ".o_tour_pointer");
        await click(target, "button.inc");
        assert.containsNone(document.body, ".o_tour_pointer");
        assert.strictEqual(target.querySelector("span.value").textContent, "1");
    });

    QUnit.test("perform edit on next step", async function (assert) {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: [
                {
                    trigger: ".interval input",
                },
                {
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: TourPointerContainer, props: tourPointerProps } = registry
            .category("main_components")
            .get("TourPointerContainer");

        class Root extends Component {
            static components = { TourPointerContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <TourPointerContainer t-props="props.tourPointerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { tourPointerProps } });
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

    QUnit.test("should show only 1 pointer at a time", async function (assert) {
        registry.category("web_tour.tours").add("tour1", {
            sequence: 10,
            steps: [
                {
                    trigger: ".interval input",
                },
            ],
        });
        registry.category("web_tour.tours").add("tour2", {
            sequence: 10,
            steps: [
                {
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: TourPointerContainer, props: tourPointerProps } = registry
            .category("main_components")
            .get("TourPointerContainer");

        class Root extends Component {
            static components = { TourPointerContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <TourPointerContainer t-props="props.tourPointerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { tourPointerProps } });
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
            steps: [
                {
                    content: "content",
                    trigger: "button.inc",
                },
            ],
        });
        const env = await makeTestEnv({});

        const { Component: TourPointerContainer, props: tourPointerProps } = registry
            .category("main_components")
            .get("TourPointerContainer");

        class Root extends Component {
            static components = { TourPointerContainer, Counter };
            static template = xml/*html*/ `
                <t>
                    <Counter />
                    <TourPointerContainer t-props="props.tourPointerProps" />
                </t>
            `;
        }

        await mount(Root, target, { env, props: { tourPointerProps } });
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
});
