/** @odoo-module **/

import {
    advanceTime,
    after,
    animationFrame,
    beforeEach,
    describe,
    expect,
    getFixture,
    press,
    queryFirst,
    test,
    waitFor,
    waitForNone,
    waitUntil,
} from "@odoo/hoot";
import { Component, onMounted, onPatched, proxy, xml } from "@odoo/owl";
import {
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { location, browser } from "@web/core/browser/browser";
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";
import { TourInteractive } from "@web_tour/tour_interactive/tour_interactive";
import { TourInteractiveObserver } from "@web_tour/tour_interactive/tour_interactive_observer";
import { TourPointer, pointerState } from "@web_tour/tour_pointer/tour_pointer";
import { Tour, TourStep } from "./tour_models";

describe.current.tags("desktop");

class Partner extends models.Model {
    _name = "partner";

    m2o = fields.Many2one({ relation: "product" });

    _views = {
        form: `<form>
            <field name="m2o"/>
        </form>`,
    };
}

class Product extends models.Model {
    _name = "product";

    name = fields.Char();

    _records = [{ name: "A" }, { name: "B" }];
}

defineModels([Partner, Product, Tour, TourStep]);

class Counter extends Component {
    static template = xml/*html*/ `
        <div class="counter">
            <div class="interval">
                <input type="number" t-model.proxy.number="this.state.interval" />
            </div>
            <div class="counter">
                <span class="value" t-out="this.state.value" />
                <button class="inc" t-on-click="this.onIncrement">+</button>
            </div>
        </div>
    `;
    setup() {
        this.state = proxy({ interval: 1, value: 0 });
    }
    onIncrement() {
        this.state.value += this.state.interval;
    }
}

const tourRegistry = registry.category("web_tour.tours");
const tourConsumed = [];

beforeEach(() => {
    patchWithCleanup(console, {
        error: () => {},
        warn: () => {},
        log: () => {},
        dir: () => {},
    });
    onRpc("web_tour.tour", "consume", ({ args }) => {
        tourConsumed.push(args[0]);
        const nextTour = tourRegistry
            .getEntries()
            .filter(([tourName]) => !tourConsumed.includes(tourName))
            .at(0);
        return (nextTour && { name: nextTour.at(0) }) || false;
    });
    onRpc("res.users", "switch_tour_enabled", () => true);
});

after(() => {
    TourInteractive.current?.stop();
});

test("registering test tour after service is started doesn't auto-start the tour", async () => {
    Tour._records = [{ name: "tour1" }];
    patchWithCleanup(session, { tour_enabled: true });
    class Root extends Component {
        static components = { Counter };
        static template = xml/*html*/ `
                <t>
                    <Counter />
                </t>
            `;
    }

    await mountWithCleanup(Root);
    expect(".o_tour_pointer").toHaveCount(0);
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            {
                content: "content",
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("perform edit on next step", async () => {
    Tour._records = [{ name: "giro_d_italia" }];
    registry.category("web_tour.tours").add("giro_d_italia", {
        steps: () => [
            {
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = { Counter };
        static template = xml/*html*/ `
            <t>
                <Counter />
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("giro_d_italia", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains(".interval input").edit(5);
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains("button.inc").click();
    await animationFrame();
    expect(".counter .value").toHaveText("5");
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("robot mode performs every step automatically, without any human interaction", async () => {
    Tour._records = [{ name: "tour_robot" }];
    registry.category("web_tour.tours").add("tour_robot", {
        steps: () => [
            {
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = { Counter };
        static template = xml/*html*/ `
            <t>
                <Counter />
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_robot", { mode: "manual", robot: true });
    await waitFor(".o_tour_pointer");
    await waitForNone(".o_tour_pointer");
    expect(".counter .value").toHaveText("5");
});

test("robot mode waits for its trigger to re-enable if it got disabled after being resolved", async () => {
    Tour._records = [{ name: "tour_robot_disabled" }];
    registry.category("web_tour.tours").add("tour_robot_disabled", {
        steps: () => [
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    const state = proxy({ disabled: false, value: 0 });
    class Root extends Component {
        static template = xml/*html*/ `
            <t>
                <button class="inc" t-att-disabled="this.state.disabled" t-on-click="this.onClick">+</button>
            </t>
        `;
        setup() {
            this.state = state;
        }
        onClick() {
            this.state.value++;
        }
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_robot_disabled", {
        mode: "manual",
        robot: true,
    });
    state.disabled = true;
    await waitFor(".o_tour_pointer");
    expect(queryFirst("button.inc")).toHaveProperty("disabled", true);
    expect(state.value).toBe(0);
    state.disabled = false;
    await waitForNone(".o_tour_pointer");
    expect(state.value).toBe(1);
});

test("manual tour with inactive steps", async () => {
    Tour._records = [{ name: "tour_de_wallonie" }];
    registry.category("web_tour.tours").add("tour_de_wallonie", {
        steps: () => [
            {
                isActive: ["auto"],
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                isActive: ["auto"],
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                isActive: ["manual"],
                trigger: ".interval input",
                run: "edit 5",
            },
            {
                isActive: ["auto"],
                trigger: "button.inc",
                run: "click",
            },
            {
                isActive: ["auto"],
                trigger: "button.inc",
                run: "click",
            },
            {
                isActive: ["manual"],
                trigger: "button.inc",
                run: "click",
            },
            {
                isActive: ["auto"],
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = { Counter };
        static template = xml/*html*/ `
            <t>
                <Counter />
            </t>
        `;
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_de_wallonie", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains(".interval input").edit(5);
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains("button.inc").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
    expect(".counter .value").toHaveText("5");
});

test("manual tour with alternative trigger", async () => {
    patchWithCleanup(browser.console, {
        log: (s) => {
            !s.includes("═") ? expect.step(s) : "";
        },
    });
    TourStep._records = [
        {
            tour_id: 1,
            trigger: ".button, .button2",
            run: "click",
        },
        {
            tour_id: 1,
            trigger: "body:not(:visible), .button4, .button3",
            run: "click",
        },
        {
            tour_id: 1,
            trigger: ".interval1, .interval2, .button5",
            run: "click",
        },
        {
            tour_id: 1,
            trigger: "button:contains(hellow):enabled, button:contains(youpi)",
            run: "click",
        },
    ];
    Tour._records = [
        {
            id: 1,
            name: "tour_des_flandres_2",
        },
    ];
    class Root extends Component {
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <button class="button0">0, hello</button>
                    <button class="button1">Button 1</button>
                    <button class="button2">2, youpi</button>
                    <button class="button3">Button 3</button>
                    <button class="button4">Button 4</button>
                    <button class="button5">Button 5</button>
                </div>
            </t>
        `;
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres_2", {
        mode: "manual",
        fromDB: true,
    });
    await contains(".button2").click();
    await contains(".button4").click();
    await contains(".button5").click();
    await contains(".button2").click();
    expect.verifySteps(["click", "click", "click", "click", "tour succeeded"]);
});

test("Tour backward when the pointed element disappear", async () => {
    Tour._records = [{ name: "tour1" }];
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        state = proxy({ bool: true });
        static template = xml`
            <button class="fool w-100" t-on-click="() => { this.state.bool = true; }">You fool</button>
            <button class="foo w-100" t-if="this.state.bool" t-on-click="() => { this.state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!this.state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.fool").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.foo"));
    await waitFor(".o_tour_pointer");

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("Tour backward when the pointed element disappear and ignore warn step", async () => {
    Tour._records = [
        {
            id: 1,
            name: "tour1",
        },
    ];
    TourStep._records = [
        { trigger: "button.foo", run: "click", tour_id: 1 },
        { trigger: "button.foo", tour_id: 1 },
        { trigger: "button.bar", run: "click", tour_id: 1 },
    ];
    patchWithCleanup(console, {
        log: (msg) => {
            if (typeof msg === "string" && msg.endsWith("ignored.")) {
                expect.step(msg);
            }
        },
    });

    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.foo" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        state = proxy({ bool: true });
        static template = xml`
            <button class="fool" t-on-click="() => { this.state.bool = true; }">You fool</button>
            <button class="foo" t-if="this.state.bool" t-on-click="() => { this.state.bool = false; }">Foo</button>
            <button class="bar" t-if="!this.state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.fool").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.foo"));
    await waitFor(".o_tour_pointer");

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
    expect.verifySteps(["Step 'button.foo' ignored.", "Step 'button.foo' ignored."]);
});

test("Lost tour goes backward as soon as a previous trigger is back", async () => {
    Tour._records = [{ name: "tour1" }];
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        state = proxy({ page: "foo" });
        static template = xml`
            <button class="other w-100" t-on-click="() => { this.state.page = 'other'; }">Other</button>
            <button class="back w-100" t-on-click="() => { this.state.page = 'foo'; }">Back</button>
            <button class="foo w-100" t-if="this.state.page === 'foo'" t-on-click="() => { this.state.page = 'bar'; }">Foo</button>
            <button class="bar w-100" t-if="this.state.page === 'bar'">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await waitUntil(() => pointerState.trigger === queryFirst("button.foo"));

    await contains("button.foo").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.bar"));

    await contains("button.other").click();
    await waitForNone(".o_tour_pointer");

    await contains("button.back").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.foo"));

    await contains("button.foo").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.bar"));
    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("Tour only looks for a previous trigger among the last actions when going backward", async () => {
    Tour._records = [{ name: "tour1" }];
    const pages = [...Array(TourInteractive.MAX_BACKWARD_ACTIONS + 1).keys()].map((i) => i + 1);
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.first", run: "click" },
            ...pages.map((page) => ({ trigger: `button.page${page}`, run: "click" })),
        ],
    });

    class Dummy extends Component {
        state = proxy({ page: 0 });
        pages = pages;
        static template = xml`
            <button class="first w-100" t-on-click="() => { this.state.page = 1; }">First</button>
            <button class="away w-100" t-on-click="() => { this.state.page = 0; }">Away</button>
            <button class="back w-100" t-on-click="() => { this.state.page = 5; }">Back</button>
            <t t-foreach="this.pages" t-as="page" t-key="page">
                <button t-if="this.state.page === page" t-attf-class="page{{page}} w-100" t-on-click="() => { this.state.page = page + 1; }">Page</button>
            </t>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await waitUntil(() => pointerState.trigger === queryFirst("button.first"));
    await contains("button.first").click();
    for (const page of pages.slice(0, -1)) {
        await waitUntil(() => pointerState.trigger === queryFirst(`button.page${page}`));
        await contains(`button.page${page}`).click();
    }
    await waitUntil(() => pointerState.trigger === queryFirst(`button.page${pages.at(-1)}`));

    await contains("button.away").click();
    await waitForNone(".o_tour_pointer");
    await animationFrame();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);

    await contains("button.back").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.page5"));
});
test("Tour started by the URL", async () => {
    Tour._records = [
        {
            id: 1,
            name: "tour1",
        },
    ];
    TourStep._records = [
        { trigger: "button.foo", run: "click", tour_id: 1 },
        { trigger: "button.foo", tour_id: 1 },
        { trigger: "button.bar", run: "click", tour_id: 1 },
    ];
    location.href = `${location.origin}?tour=tour1`;

    class Dummy extends Component {
        state = proxy({ bool: true });
        static template = xml`
            <button class="foo w-100" t-if="this.state.bool" t-on-click="() => { this.state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!this.state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("Log a warning if step ignored", async () => {
    Tour._records = [{ name: "tour1" }];
    patchWithCleanup(console, {
        log: (msg) => {
            if (typeof msg === "string" && msg.endsWith("ignored.")) {
                expect.step(msg);
            }
        },
    });
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        state = proxy({ bool: true });
        static template = xml`
            <button class="foo w-100" t-if="this.state.bool" t-on-click="() => { this.state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!this.state.bool">Bar</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);

    expect.verifySteps(["Step 'button.bar' ignored."]);
});

test("check alternative trigger that appear after the initial trigger", async () => {
    Tour._records = [{ name: "rainbow_tour" }];
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".buttonnnnnn, .button1",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3"><button class="button0">Button 0</button></div>
                    <div class="p-3 add_button"></div>
                </div>
            </t>
        `;
    }
    await mountWithCleanup(Root);
    getService("tour_service").startTour("rainbow_tour", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
    const otherButton = document.createElement("button");
    otherButton.classList.add("button1");
    queryFirst(".add_button").appendChild(otherButton);
    await waitFor(".o_tour_pointer");
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".button1").click();
    await waitForNone(".o_tour_pointer");
});

test("validating edit step on autocomplete by selecting autocomplete item", async () => {
    Tour._records = [{ name: "rainbow_tour" }];
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".o-autocomplete--input",
                run: "edit A",
            },
            {
                trigger: ".o_form_button_save",
                run: "click",
            },
        ],
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });
    getService("tour_service").startTour("rainbow_tour", { mode: "manual" });
    await animationFrame();

    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item:first-child").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("validating edit step on autocomplete by selecting autocomplete item (validate automatically autocomplete item step)", async () => {
    Tour._records = [{ name: "rainbow_tour" }];
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".o-autocomplete--input",
                run: "edit A",
            },
            {
                trigger: ".o-autocomplete--dropdown-item:first-child",
                run: "click",
            },
            {
                trigger: ".o_form_button_save",
                run: "click",
            },
        ],
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });
    getService("tour_service").startTour("rainbow_tour", { mode: "manual" });
    await animationFrame();

    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item:first-child").click();
    await waitUntil(() => pointerState.trigger === queryFirst(".o_form_button_save"));
    await waitFor(".o_tour_pointer");
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("validating click on autocomplete item by pressing Enter", async () => {
    Tour._records = [{ name: "rainbow_tour" }];
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".o-autocomplete--input",
                run: "click",
            },
            {
                trigger: ".o-autocomplete--dropdown-item:first-child",
                run: "click",
            },
            {
                trigger: ".o_form_button_save",
                run: "click",
            },
        ],
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });
    getService("tour_service").startTour("rainbow_tour", { mode: "manual" });
    await waitFor(".o_tour_pointer_tip");
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains(".o-autocomplete--input").click();
    await waitFor(".o_tour_pointer_tip");
    await press("Enter");
    await waitUntil(() => pointerState.trigger === queryFirst(".o_form_button_save"));
    await waitFor(".o_tour_pointer_tip");
    await contains(".o_form_button_save").click();
    await waitForNone(".o_tour_pointer_tip");
});

test("Tour don't backward when dropdown loading", async () => {
    Tour._records = [{ name: "rainbow_tour" }];
    Product._records = [{ name: "Harry test 1" }, { name: "Harry test 2" }];
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".o-autocomplete--input",
                run: "click",
            },
            {
                trigger: ".o-autocomplete--dropdown-item:eq(1)",
                run: "click",
            },
            {
                trigger: ".o_form_button_save",
                run: "click",
            },
        ],
    });

    const def = Promise.withResolvers();
    let makeItLag = false;
    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    onRpc("product", "web_name_search", async () => {
        if (makeItLag) {
            await def.promise;
        }
    });

    getService("tour_service").startTour("rainbow_tour", { mode: "manual" });
    await waitFor(".o_tour_pointer_tip");

    expect(".o_tour_pointer_tip").toHaveCount(1);
    makeItLag = true;
    await contains(".o-autocomplete--input").click();
    await waitFor(".o-autocomplete--dropdown-item:eq(0)");
    await contains(".o-autocomplete--input").fill("Harry", { confirm: false });
    await advanceTime(400);
    await waitFor(".o_loading");
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
    def.resolve();

    await waitFor(".o-autocomplete--dropdown-item:eq(1)");
    await waitFor(".o_tour_pointer_tip");
    await contains(".o-autocomplete--dropdown-item:eq(1)").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    expect(".o-autocomplete--input").toHaveValue("Harry test 2");
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("edit step on autocomplete input is not consumed by the first keystroke", async () => {
    Tour._records = [{ name: "create_tour" }];
    registry.category("web_tour.tours").add("create_tour", {
        steps: () => [
            {
                trigger: ".o-autocomplete--input",
                run: "edit Zorro",
            },
            {
                trigger: ".o_m2o_dropdown_option_create_edit a",
                run: "click",
            },
            {
                trigger: ".modal-content button.btn-primary",
                run: "click",
            },
        ],
    });

    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    onRpc("product", "web_name_search", () => []);

    getService("tour_service").startTour("create_tour", { mode: "manual" });
    await waitFor(".o_tour_pointer_tip");

    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--input").fill("Zorro", { confirm: false });
    await animationFrame();
    expect(".o-autocomplete--input").toHaveValue("Zorro");

    await waitFor(".o_m2o_dropdown_option_create_edit a");
    await contains(".o_m2o_dropdown_option_create_edit a").click();
    await animationFrame();

    await waitFor(".modal-content button.btn-primary");
    expect(".o_tour_pointer_tip").toHaveCount(1);
});

test("Don't backward when action manager is busy", async () => {
    Tour._records = [{ name: "tour1" }];
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        state = proxy({ bool: true });
        static template = xml`
            <button class="fool w-100" t-on-click="() => { this.state.bool = true; }">You fool</button>
            <button class="foo w-100" t-if="this.state.bool" t-on-click="() => { this.state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!this.state.bool">Bar</button>
        `;
    }

    const comp = await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    comp.env.bus.trigger("ACTION_MANAGER:UPDATE");
    await animationFrame();

    await contains("button.fool").click();
    await waitForNone(".o_tour_pointer");

    await contains("button.foo").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.bar"));
    await waitFor(".o_tour_pointer");

    comp.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");

    await contains("button.fool").click();
    await waitUntil(() => pointerState.trigger === queryFirst("button.foo"));
    await waitFor(".o_tour_pointer");

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("check rainbowManMessage", async () => {
    Tour._records = [{ name: "rainbow_tour" }];
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".button0",
                run: "click",
            },
            {
                trigger: ".button1",
                run: "click",
            },
            {
                trigger: ".button2",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3"><button class="button0">Button 0</button></div>
                    <div class="p-3"><button class="button1">Button 1</button></div>
                    <div class="p-3"><button class="button2">Button 2</button></div>
                </div>
            </t>
        `;
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("rainbow_tour", {
        mode: "manual",
        rainbowManMessage: "Congratulations !",
    });
    await contains(".button0").click();
    await contains(".button1").click();
    await contains(".button2").click();
    const rainbowMan = await waitFor(".o_reward_rainbow_man");
    expect(rainbowMan.getBoundingClientRect().width).toBe(400);
    expect(rainbowMan.getBoundingClientRect().height).toBe(400);
    expect(".o_reward_msg_content").toHaveText("Congratulations !");
});

test("pointer hidden when trigger is behind overlay", async () => {
    Tour._records = [{ name: "tour1" }];
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [{ trigger: "button.foo", run: "click" }],
    });

    class DummyDialog extends Component {
        static components = { Dialog };
        static template = xml`
            <Dialog>
                <button class="a">A</button>
            </Dialog>
        `;
    }

    class Dummy extends Component {
        static template = xml`
            <button class="foo w-100">Foo</button>
        `;
    }

    await mountWithCleanup(Dummy);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await waitFor(".o_tour_pointer");
    getService("dialog").add(DummyDialog, {});
    await waitFor(".modal");
    await waitForNone(".o_tour_pointer");
    await contains(".modal .btn-close").click();
    await waitFor(".o_tour_pointer");
    // Finalize the dummy tour to avoid leaving in a dirty state
    await contains("button.foo").click();
});

test("start a tour that no longer exist should clear tourstate", async () => {
    Tour._records = [{ name: "tour69" }];
    registry.category("web_tour.tours").add("tour69", {
        steps: () => [{ trigger: "button.foo", run: "click" }],
    });
    class Root extends Component {
        static components = { Counter };
        static template = xml/*html*/ `
                <t>
                    <Counter />
                </t>
            `;
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour69", { mode: "manual", fromDB: true });
    expect(browser.localStorage.getItem("current_tour")).toBe("tour69");
    registry.category("web_tour.tours").remove("tour69");
    await getService("tour_service").startTour("tour69", { mode: "manual", fromDB: true });
    expect(browser.localStorage.getItem("current_tour")).toBe(null);
});

test("avoid rendering loop of pointer", async () => {
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [{ trigger: "button.foo", run: "click" }],
    });
    Tour._records = [{ name: "tour1" }];
    let patchCount = 0;
    patchWithCleanup(TourPointer.prototype, {
        setup() {
            super.setup();
            onMounted(() => {
                patchCount++;
            });
            onPatched(() => {
                patchCount++;
            });
        },
    });
    const state = proxy({ hasFoo: true });
    class Dummy extends Component {
        static template = xml`
            <div class="o_home_menu">Dummy menu to allow pointer to disappear</div>
            <button t-if="this.state.hasFoo" class="foo w-100">Foo</button>
        `;

        state = state;
    }
    await mountWithCleanup(Dummy);
    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await waitFor(".o_tour_pointer");
    expect(patchCount).toBe(1);
    await animationFrame();
    expect(patchCount).toBe(2);
    await animationFrame();
    expect(patchCount).toBe(2);

    state.hasFoo = false;
    await waitForNone(".o_tour_pointer");
    expect(patchCount).toBe(3);
    await animationFrame();
    expect(patchCount).toBe(3);
});

test("robot mode logs an error and removes the pointer when a step times out", async () => {
    Tour._records = [{ name: "tour_robot_timeout" }];
    registry.category("web_tour.tours").add("tour_robot_timeout", {
        steps: () => [{ trigger: "button.inc", run: "click" }],
    });
    patchWithCleanup(console, {
        error: (msg) => {
            if (typeof msg === "string" && msg.startsWith("Robot: no progress")) {
                expect.step("timeout");
            }
        },
    });
    const state = proxy({ disabled: false });
    class Root extends Component {
        static template = xml`<button class="inc" t-att-disabled="this.state.disabled">+</button>`;
        setup() {
            this.state = state;
        }
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_robot_timeout", {
        mode: "manual",
        robot: true,
    });
    state.disabled = true;
    await waitFor(".o_tour_pointer");

    await advanceTime(10000);
    await animationFrame();
    expect.verifySteps(["timeout"]);
    expect(".o_tour_pointer").toHaveCount(0);
});

test("failed drop goes back to the drag action", async () => {
    Tour._records = [{ name: "tour_dnd" }];
    registry.category("web_tour.tours").add("tour_dnd", {
        steps: () => [
            { trigger: ".drag-src", run: "drag_and_drop .drop-zone" },
            { trigger: "button.done", run: "click" },
        ],
    });

    const state = proxy({ blocked: true });
    class Root extends Component {
        static template = xml`
            <div class="drag-src" style="width: 50px; height: 50px;">Drag</div>
            <div class="drop-zone" t-att-style="'width: 100px; height: 100px;' + (this.state.blocked ? 'pointer-events: none;' : '')">Zone</div>
            <button class="done w-100">Done</button>
        `;
        setup() {
            this.state = state;
        }
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_dnd", { mode: "manual" });
    await waitUntil(() => pointerState.trigger === queryFirst(".drag-src"));

    let dragActions = await contains(".drag-src").drag();
    await waitUntil(() => pointerState.trigger === queryFirst(".drop-zone"));
    await dragActions.moveTo("button.done");
    await dragActions.drop();
    await waitUntil(() => pointerState.trigger === queryFirst(".drag-src"));

    state.blocked = false;
    await animationFrame();
    dragActions = await contains(".drag-src").drag();
    await waitUntil(() => pointerState.trigger === queryFirst(".drop-zone"));
    await dragActions.moveTo(".drop-zone");
    await dragActions.drop();
    await waitUntil(() => pointerState.trigger === queryFirst("button.done"));

    await contains("button.done").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("edit step on autocomplete as last step can be validated by selecting an item", async () => {
    Tour._records = [{ name: "last_autocomplete_tour" }];
    registry.category("web_tour.tours").add("last_autocomplete_tour", {
        steps: () => [{ trigger: ".o-autocomplete--input", run: "edit A" }],
    });

    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });
    getService("tour_service").startTour("last_autocomplete_tour", { mode: "manual" });
    await waitFor(".o_tour_pointer");

    await contains(".o-autocomplete--input").click();
    await contains(".o-autocomplete--dropdown-item:first-child").click();
    await waitUntil(() => tourConsumed.includes("last_autocomplete_tour"));
    expect(".o_tour_pointer").toHaveCount(0);
});

test("finished tour is released and no longer listens to the bus", async () => {
    Tour._records = [{ name: "release_tour" }];
    registry.category("web_tour.tours").add("release_tour", {
        steps: () => [{ trigger: "button.foo", run: "click" }],
    });

    class Root extends Component {
        static template = xml`<button class="foo w-100">Foo</button>`;
    }

    const comp = await mountWithCleanup(Root);
    await getService("tour_service").startTour("release_tour", { mode: "manual" });
    await waitFor(".o_tour_pointer");
    const tour = TourInteractive.current;

    await contains("button.foo").click();
    await waitUntil(() => tourConsumed.includes("release_tour"));
    expect(TourInteractive.current).toBe(null);

    comp.env.bus.trigger("ACTION_MANAGER:UPDATE");
    expect(tour.isBusy).toBe(false);
});

test("trigger is only looked for again once the DOM changed or the periodic check fired", async () => {
    Tour._records = [{ name: "search_flag_tour" }];
    registry.category("web_tour.tours").add("search_flag_tour", {
        steps: () => [{ trigger: "button.bar", run: "click" }],
    });
    let searches = 0;
    patchWithCleanup(TourInteractive.prototype, {
        track() {
            searches++;
            return super.track(...arguments);
        },
    });
    const state = proxy({ showBar: false, value: 0 });
    class Root extends Component {
        static template = xml`
            <span class="value" t-out="this.state.value"/>
            <button class="bar w-100" t-if="this.state.showBar">Bar</button>
        `;
        setup() {
            this.state = state;
        }
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("search_flag_tour", { mode: "manual" });
    await animationFrame();
    await animationFrame();
    const initialSearches = searches;
    expect(initialSearches).toBeGreaterThan(0);

    await animationFrame();
    await animationFrame();
    await animationFrame();
    expect(searches).toBe(initialSearches);

    state.value++;
    await animationFrame();
    await animationFrame();
    await animationFrame();
    expect(searches).toBe(initialSearches + 1);

    await advanceTime(TourInteractiveObserver.CHECK_INTERVAL);
    await animationFrame();
    expect(searches).toBe(initialSearches + 2);

    state.showBar = true;
    await waitFor(".o_tour_pointer");
});

test("a change inside a shadow root added after the start triggers a new search", async () => {
    Tour._records = [{ name: "shadow_tour" }];
    registry.category("web_tour.tours").add("shadow_tour", {
        steps: () => [{ trigger: ".host:shadow button.bar", run: "click" }],
    });
    let searches = 0;
    patchWithCleanup(TourInteractive.prototype, {
        track() {
            searches++;
            return super.track(...arguments);
        },
    });
    class Root extends Component {
        static template = xml`<div class="o_root"/>`;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("shadow_tour", { mode: "manual" });
    await animationFrame();

    const host = document.createElement("div");
    host.classList.add("host");
    const shadowRoot = host.attachShadow({ mode: "open" });
    const wrapper = document.createElement("div");
    wrapper.append(host);
    getFixture().append(wrapper);
    await animationFrame();
    await animationFrame();
    const searchesBeforeShadowChange = searches;

    shadowRoot.innerHTML = `<span>Changed</span>`;
    await animationFrame();
    await animationFrame();
    await animationFrame();
    expect(searches).toBe(searchesBeforeShadowChange + 1);
});
