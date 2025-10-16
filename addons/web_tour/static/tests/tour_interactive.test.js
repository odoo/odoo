/** @odoo-module **/

import { after, beforeEach, describe, expect, test } from "@odoo/hoot";
import { queryFirst, waitFor, press, Deferred } from "@odoo/hoot-dom";
import { advanceTime, animationFrame } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import {
    contains,
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    models,
    fields,
    defineModels,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";
import { TourInteractive } from "@web_tour/js/tour_interactive/tour_interactive";

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

defineModels([Partner, Product]);

class Counter extends Component {
    static props = ["*"];
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
    onRpc("web_tour.tour", "get_tour_json_by_name", () => ({
        name: "tour1",
        steps: [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    }));
});

after(() => {
    TourInteractive.observer.disconnect();
});

test("registering test tour after service is started doesn't auto-start the tour", async () => {
    patchWithCleanup(session, { tour_enabled: true });
    class Root extends Component {
        static components = { Counter };
        static template = xml/*html*/ `
                <t>
                    <Counter />
                </t>
            `;
        static props = ["*"];
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
        static props = ["*"];
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

test("manual tour with inactive steps", async () => {
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
        static props = ["*"];
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
    registry.category("web_tour.tours").add("tour_des_flandres_2", {
        steps: () => [
            {
                trigger: ".button1, .button2",
                run: "click",
            },
            {
                trigger: "body:not(:visible), .button4, .button3",
                run: "click",
            },
            {
                trigger: ".interval1, .interval2, .button5",
                run: "click",
            },
            {
                trigger: "button:contains(0, hello):enabled, button:contains(2, youpi)",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = {};
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
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres_2", { mode: "manual" });
    await contains(".button2").click();
    await contains(".button3").click();
    await contains(".button5").click();
    await contains(".button2").click();
    expect.verifySteps(["click", "click", "click", "click", "tour succeeded"]);
});

test("Tour backward when the pointed element disappear", async () => {
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="fool w-100" t-on-click="() => { state.bool = true; }">You fool</button>
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
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
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("Tour backward when the pointed element disappear and ignore warn step", async () => {
    patchWithCleanup(console, {
        warn: (msg) => expect.step(msg),
    });

    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="fool" t-on-click="() => { state.bool = true; }">You fool</button>
            <button class="foo" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar" t-if="!state.bool">Bar</button>
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
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
    expect.verifySteps(["Step 'button.bar' ignored.", "Step 'button.bar' ignored."]);
});

test("Tour started by the URL", async () => {
    browser.location.href = `${browser.location.origin}?tour=tour1`;

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
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
    patchWithCleanup(console, {
        warn: (msg) => expect.step(msg),
    });

    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
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
    registry.category("web_tour.tours").add("rainbow_tour", {
        steps: () => [
            {
                trigger: ".button0, .button1",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3"><button class="button0">Button 0</button></div>
                    <div class="p-3 add_button"></div>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    getService("tour_service").startTour("rainbow_tour", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    const otherButton = document.createElement("button");
    otherButton.classList.add("button1");
    queryFirst(".add_button").appendChild(otherButton);
    await contains(".button1").click();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("validating edit step on autocomplete by selecting autocomplete item", async () => {
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
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("validating click on autocomplete item by pressing Enter", async () => {
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
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await press("Enter");
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("Tour don't backward when dropdown loading", async () => {
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

    const def = new Deferred();
    let makeItLag = false;
    await mountWithCleanup(WebClient);

    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [[false, "form"]],
    });

    onRpc("product", "web_name_search", async () => {
        if (makeItLag) {
            await def;
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
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    await contains(".o-autocomplete--dropdown-item:eq(1)").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(1);
    expect(".o-autocomplete--input").toHaveValue("Harry test 2");
    await contains(".o_form_button_save").click();
    await animationFrame();
    expect(".o_tour_pointer_tip").toHaveCount(0);
});

test("Don't backward when action manager is busy", async () => {
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static components = {};
        static template = xml`
            <button class="fool w-100" t-on-click="() => { state.bool = true; }">You fool</button>
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
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
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    comp.env.bus.trigger("ACTION_MANAGER:UI-UPDATED");

    await contains("button.fool").click();
    await animationFrame();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("check rainbowManMessage", async () => {
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
        static components = {};
        static template = xml/*html*/ `
            <t>
                <div class="container">
                    <div class="p-3"><button class="button0">Button 0</button></div>
                    <div class="p-3"><button class="button1">Button 1</button></div>
                    <div class="p-3"><button class="button2">Button 2</button></div>
                </div>
            </t>
        `;
        static props = ["*"];
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
