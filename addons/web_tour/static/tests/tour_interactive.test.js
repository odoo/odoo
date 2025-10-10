/** @odoo-module **/

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, hover, leave, queryFirst, waitFor, press, Deferred, edit } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, disableAnimations, runAllTimers } from "@odoo/hoot-mock";
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
import { Dialog } from "@web/core/dialog/dialog";
import { registry } from "@web/core/registry";
import { session } from "@web/session";
import { WebClient } from "@web/webclient/webclient";

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

test("points to next step", async () => {
    tourRegistry.add("tour1", {
        steps: () => [
            {
                trigger: "button.inc",
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml`
            <t>
                <Counter />
            </t>`;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".o_tour_pointer").toHaveCount(0);
    expect("span.value").toHaveText("1");
});

test("next step with new anchor at same position", async () => {
    tourRegistry.add("tour1", {
        steps: () => [
            { trigger: "button.foo", run: "click" },
            { trigger: "button.bar", run: "click" },
        ],
    });

    class Dummy extends Component {
        static props = ["*"];
        state = useState({ bool: true });
        static template = xml/*html*/ `
            <button class="foo w-100" t-if="state.bool" t-on-click="() => { state.bool = false; }">Foo</button>
            <button class="bar w-100" t-if="!state.bool">Bar</button>
        `;
    }
    class Root extends Component {
        static props = ["*"];
        static components = { Dummy };
        static template = xml/*html*/ `
            <t>
                <Dummy />
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour1", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    // check position of the pointer relative to the foo button
    let pointerRect = queryFirst(".o_tour_pointer").getBoundingClientRect();
    let buttonRect = queryFirst("button.foo").getBoundingClientRect();
    const leftValue1 = pointerRect.left - buttonRect.left;
    const bottomValue1 = pointerRect.bottom - buttonRect.bottom;
    expect(leftValue1).not.toBe(0);
    expect(bottomValue1).not.toBe(0);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    // check position of the pointer relative to the bar button
    pointerRect = queryFirst(".o_tour_pointer").getBoundingClientRect();
    buttonRect = queryFirst("button.bar").getBoundingClientRect();
    const leftValue2 = pointerRect.left - buttonRect.left;
    const bottomValue2 = pointerRect.bottom - buttonRect.bottom;
    expect(Math.round(bottomValue1)).toBe(Math.round(bottomValue2));
    expect(leftValue1).toBe(leftValue2);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("pointer is added on top of overlay's stack", async () => {
    registry.category("web_tour.tours").add("tour1", {
        steps: () => [
            { trigger: ".modal .a", run: "click" },
            { trigger: ".modal .btn-close", run: "click" },
        ],
    });
    class DummyDialog extends Component {
        static props = ["*"];
        static components = { Dialog };
        static template = xml`
            <Dialog>
                <button class="a">A</button>
                <button class="b">B</button>
            </Dialog>
        `;
    }
    class Root extends Component {
        static props = ["*"];
        static components = {};
        static template = xml``;
    }

    await mountWithCleanup(Root);

    await getService("tour_service").startTour("tour1", { mode: "manual" });
    getService("dialog").add(DummyDialog, {});
    await advanceTime(100);
    expect(`.o-overlay-item`).toHaveCount(2);
    // the pointer should be after the dialog
    expect(".o-overlay-item:eq(0) .modal").toHaveCount(1);
    await advanceTime(100);
    expect(".o-overlay-item:eq(1) .o_tour_pointer").toHaveCount(1);

    await click(".modal .a");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await click(".modal .btn-close");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
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

test("hovering to the anchor element should show the content and not when content empty", async () => {
    registry.category("web_tour.tours").add("la_vuelta", {
        steps: () => [
            {
                content: "content",
                trigger: "button.inc",
                run: "click",
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
                <button class="other">Pogačar</button>
            </t>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("la_vuelta", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").hover();
    await animationFrame();
    expect(".o_tour_pointer_content:not(.invisible)").toHaveCount(1);
    expect(".o_tour_pointer_content:not(.invisible) span").toHaveText("content");
    await contains(".other").hover();
    await animationFrame();
    expect(".o_tour_pointer_content.invisible").toHaveCount(1);

    await click("button.inc");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").hover();
    await animationFrame();
    expect(".o_tour_pointer_content.invisible").toHaveCount(1);

    await click("button.inc");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("should show only 1 pointer at a time", async () => {
    registry.category("web_tour.tours").add("milan_sanremo", {
        steps: () => [
            {
                trigger: ".interval input",
                run: "edit 5",
            },
        ],
    });
    registry.category("web_tour.tours").add("paris_roubaix", {
        steps: () => [
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
    await getService("tour_service").startTour("paris_roubaix", { mode: "manual" });
    await getService("tour_service").startTour("milan_sanremo", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    expect(".o_tour_pointer").toHaveCount(1);
    await click("button.inc");
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
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".counter .value").toHaveText("5");
    expect(".o_tour_pointer").toHaveCount(0);
});

test("scrolling to next step should update the pointer's height", async (assert) => {
    disableAnimations();

    const content = "Click this pretty button to increment this magnificent counter !";
    registry.category("web_tour.tours").add("tour_de_france", {
        steps: () => [
            {
                trigger: "button.inc",
                content,
                run: "click",
            },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <div class="scrollable-parent" style="overflow-y: scroll; height: 150px;">
                <Counter />
                <div class="bottom-filler" style="height: 300px" />
                <button class="other">Vingegaard</button>
            </div>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_de_france", { mode: "manual" });
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    expect(".o_tour_pointer").not.toHaveClass("o_open");
    const firstOpenHeight = queryFirst(".o_tour_pointer").style.height;
    const firstOpenWidth = queryFirst(".o_tour_pointer").style.width;
    expect(firstOpenHeight).toBe("28px");
    expect(firstOpenWidth).toBe("28px");

    await contains("button.inc").hover();
    expect(".o_tour_pointer span").toHaveText(content);
    expect(".o_tour_pointer").toHaveClass("o_open");
    await contains(".interval input").hover();
    expect(".o_tour_pointer").not.toHaveClass("o_open");

    await contains(".scrollable-parent").scroll({ top: 1000 });
    await runAllTimers();
    await animationFrame(); // awaits the intersection observer to update after the scroll
    // now the scroller pointer should be shown
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_tour_pointer").hover();
    await animationFrame();
    expect(".o_tour_pointer span").toHaveText("Scroll up to reach the next step.");
    await contains(".o_tour_pointer").click();

    await runAllTimers();
    // awaits the intersection observer to update after the scroll
    await animationFrame();
    // now the true step pointer should be shown again
    expect(".o_tour_pointer").toHaveCount(1);
    expect(".o_tour_pointer").not.toHaveClass("o_open");

    await contains("button.inc").hover();
    await animationFrame();
    expect(".o_tour_pointer").toHaveClass("o_open");
    expect(".o_tour_pointer span").toHaveText(content);
    await contains(".interval input").hover();
    const secondOpenHeight = queryFirst(".o_tour_pointer").style.height;
    const secondOpenWidth = queryFirst(".o_tour_pointer").style.width;
    expect(secondOpenHeight).toEqual(firstOpenHeight);
    expect(secondOpenWidth).toEqual(firstOpenWidth);

    await contains("button.inc").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("scroller pointer to reach next step", async () => {
    disableAnimations();

    registry.category("web_tour.tours").add("tour_des_flandres", {
        steps: () => [
            { trigger: "button.inc", content: "Click to increment", run: "click" },
            { trigger: "button.test", run: "click" },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <div class="scrollable-parent" style="overflow-y: scroll; height: 150px;">
                <button class="test">Test me</button>
                <div class="top-filler" style="height: 500px" />
                <Counter />
                <div class="bottom-filler" style="height: 500px" />
            </div>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres", { mode: "manual" });
    await advanceTime(1000);

    await hover(".o_tour_pointer:empty");
    await click(waitFor(".o_tour_pointer:contains(Scroll down to reach the next step.)"));
    await leave();
    await advanceTime(1000);

    await hover(".o_tour_pointer:empty");
    await waitFor(".o_tour_pointer:contains(Click to increment)");

    expect(".counter .value").toHaveText("0");

    await click("button.inc");
    await advanceTime(1000);

    expect(".counter .value").toHaveText("1");
    expect(".o_tour_pointer").toHaveCount(1);

    await hover(".o_tour_pointer:empty");
    await click(waitFor(".o_tour_pointer:contains(Scroll up to reach the next step.)"));
    await advanceTime(1000);

    await click("button.test");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});

test("scroller pointer to reach next step (X axis)", async () => {
    patchWithCleanup(Element.prototype, {
        scrollIntoView(options) {
            super.scrollIntoView({ ...options, behavior: "instant" });
        },
    });

    registry.category("web_tour.tours").add("tour_des_flandres", {
        steps: () => [
            { trigger: "button.inc", content: "Click to increment", run: "click" },
            { trigger: "button.test", run: "click" },
        ],
    });
    class Root extends Component {
        static props = ["*"];
        static components = { Counter };
        static template = xml/*html*/ `
            <div class="scrollable-parent d-flex flex-row" style="overflow-x: scroll; width: 300px;">
                <button class="test">Test me</button>
                <div class="left-filler" style="min-width: 500px" />
                <Counter />
                <div class="right-filler" style="min-width: 500px" />
            </div>
        `;
    }

    await mountWithCleanup(Root);
    await getService("tour_service").startTour("tour_des_flandres", { mode: "manual" });
    await advanceTime(1000);

    await hover(".o_tour_pointer:empty");
    await click(waitFor(".o_tour_pointer:contains(Scroll right to reach the next step.)"));
    await leave();
    await advanceTime(1000);

    await hover(".o_tour_pointer:empty");
    await waitFor(".o_tour_pointer:contains(Click to increment)");

    expect(".counter .value").toHaveText("0");

    await click("button.inc");
    await advanceTime(1000);

    expect(".counter .value").toHaveText("1");
    expect(".o_tour_pointer").toHaveCount(1);

    await hover(".o_tour_pointer:empty");
    await click(waitFor(".o_tour_pointer:contains(Scroll left to reach the next step.)"));
    await advanceTime(1000);

    await click("button.test");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
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
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".interval input").edit(5);
    expect(".o_tour_pointer").toHaveCount(1);
    await contains("button.inc").click();
    expect(".o_tour_pointer").toHaveCount(0);
    expect(".counter .value").toHaveText("5");
    await advanceTime(10000);
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

test("check tooltip position", async () => {
    registry.category("web_tour.tours").add("tour_des_tooltip", {
        steps: () => [
            {
                trigger: ".button0",
                tooltipPosition: "right",
                run: "click",
            },
            {
                trigger: ".button1",
                tooltipPosition: "left",
                run: "click",
            },
            {
                trigger: ".button2",
                tooltipPosition: "bottom",
                run: "click",
            },
            {
                trigger: ".button3",
                tooltipPosition: "top",
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
                    <div class="p-3"><button class="button3">Button 3</button></div>
                </div>
            </t>
        `;
        static props = ["*"];
    }
    await mountWithCleanup(Root);
    let tooltip;
    await getService("tour_service").startTour("tour_des_tooltip", { mode: "manual" });

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button0 = await waitFor(".button0");
    expect(tooltip.getBoundingClientRect().left).toBeGreaterThan(
        button0.getBoundingClientRect().right
    );
    await contains(".button0").click();

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button1 = await waitFor(".button1");
    expect(tooltip.getBoundingClientRect().right).toBeLessThan(
        button1.getBoundingClientRect().left
    );
    await contains(".button1").click();

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button2 = await waitFor(".button2");
    expect(tooltip.getBoundingClientRect().top).toBeGreaterThan(
        button2.getBoundingClientRect().bottom
    );
    await contains(".button2").click();

    await animationFrame();
    await advanceTime(100);
    tooltip = await waitFor(".o_tour_pointer");
    const button3 = await waitFor(".button3");
    expect(tooltip.getBoundingClientRect().bottom).toBeLessThan(
        button3.getBoundingClientRect().top
    );
    await contains(".button3").click();
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
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_form_button_save").click();
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
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_form_button_save").click();
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
    await animationFrame();

    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o-autocomplete--input").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await press("Enter");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_form_button_save").click();
    expect(".o_tour_pointer").toHaveCount(0);
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
    await animationFrame();

    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o-autocomplete--input").click();
    await waitFor(".o-autocomplete--dropdown-item:eq(1)");
    makeItLag = true;
    await edit("Harry");
    await advanceTime(400);
    await waitFor(".o_loading");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
    def.resolve();

    await waitFor(".o-autocomplete--dropdown-item:eq(1)");
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o-autocomplete--dropdown-item:eq(1)").click();
    expect(".o_tour_pointer").toHaveCount(1);
    await contains(".o_form_button_save").click();
    expect(".o_tour_pointer").toHaveCount(0);
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
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.foo").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(1);

    await contains("button.bar").click();
    await animationFrame();
    expect(".o_tour_pointer").toHaveCount(0);
});
