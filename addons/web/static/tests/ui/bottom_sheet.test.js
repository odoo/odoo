// @ts-check

import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    defineStyle,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { router, routerBus } from "@web/core/browser/router";
import { RouterEvent } from "@web/core/events";
import { BottomSheet } from "@web/ui/bottom_sheet/bottom_sheet";

test("hardware Back closes only the topmost of stacked sheets", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }

    const sheet1 = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    const sheet2 = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    expect(router.ephemeralDepth).toBe(2);

    browser.history.back();
    expect(sheet2.state.isDismissing).toBe(true);
    expect(sheet1.state.isDismissing).toBe(false);
    expect(router.ephemeralDepth).toBe(1);

    browser.history.back();
    expect(sheet1.state.isDismissing).toBe(true);
    expect(router.ephemeralDepth).toBe(0);
});

test("hardware Back pressed while dismissing consumes the synthetic history entry", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }

    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    expect(router.ephemeralDepth).toBe(1);

    sheet.slideOut();
    expect(sheet.state.isDismissing).toBe(true);

    browser.history.back();
    expect(router.ephemeralDepth).toBe(0);
});

test("closing a non-topmost sheet does not leak its history entry", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }

    const sheet1 = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    const sheet2 = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    expect(router.ephemeralDepth).toBe(2);

    sheet1.__owl__.destroy();
    await animationFrame();
    expect(router.ephemeralDepth).toBe(2);

    sheet2.__owl__.destroy();
    await animationFrame();

    expect(router.ephemeralDepth).toBe(0);
    expect(browser.history.state?.ephemeralDepth).toBe(undefined);
});

test("a sheet's history entry keeps the router state visible", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }
    browser.history.replaceState(
        { nextState: { action: 42 } },
        "",
        browser.location.href,
    );

    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();

    expect(browser.history.state.nextState.action).toBe(42);
    expect(browser.history.state.skipRouteChange).toBe(true);

    sheet.__owl__.destroy();
    await animationFrame();
    expect(browser.history.state.nextState.action).toBe(42);
});

test("opening and closing a sheet never triggers a route change", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }
    router.pushState({ action: 42 });
    await runAllTimers();
    routerBus.addEventListener(RouterEvent.ROUTE_CHANGE, () =>
        expect.step("ROUTE_CHANGE"),
    );

    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    sheet.__owl__.destroy();
    await animationFrame();
    await runAllTimers();
    expect.verifySteps([]);

    const sheet2 = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    browser.history.back();
    await animationFrame();
    await runAllTimers();
    expect(sheet2.state.isDismissing).toBe(true);
    expect.verifySteps([]);
});

const animEnd = (sel, name) =>
    queryOne(sel).dispatchEvent(
        new AnimationEvent("animationend", { bubbles: true, animationName: name }),
    );

class AnimatedChild extends Component {
    static template = xml`<div class="sheet-child"><span class="inner-animation"/></div>`;
    static props = ["*"];
}

test("a descendant's animationend does not cut the dismiss animation short", async () => {
    let closed = 0;
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: AnimatedChild, close: () => closed++ },
    });
    await animationFrame();
    sheet.skipsAnimation = false;
    sheet.slideOut();
    await animationFrame();

    animEnd(".inner-animation", "spin");
    expect(closed).toBe(0);

    animEnd(".o_bottom_sheet_sheet", "bottom-sheet-out");
    expect(closed).toBe(1);
});

test("a descendant's animationend does not enable snapping before the slide-in ends", async () => {
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: AnimatedChild, close: () => {} },
    });
    sheet.skipsAnimation = false;
    sheet.state.isSnappingEnabled = false;
    sheet.initializeSheet();
    await animationFrame();

    animEnd(".inner-animation", "spin");
    expect(sheet.state.isSnappingEnabled).toBe(false);

    animEnd(".o_bottom_sheet_sheet", "bottom-sheet-in");
    expect(sheet.state.isSnappingEnabled).toBe(true);
});

test("the body carries the requested role, and none by default", async () => {
    await mountWithCleanup(BottomSheet, {
        props: { component: AnimatedChild, close: () => {}, role: "menu" },
    });
    await animationFrame();
    expect(".o_bottom_sheet_body").toHaveAttribute("role", "menu");

    await mountWithCleanup(BottomSheet, {
        props: { component: AnimatedChild, close: () => {} },
    });
    await animationFrame();
    expect(".o_bottom_sheet_body:last").not.toHaveAttribute("role");
});

test("a hosted component receives a bound close, like it does from a popover", async () => {
    /** @type {any} */
    let childProps = null;
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
        setup() {
            childProps = this.props;
        }
    }

    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => expect.step("close") },
    });
    await animationFrame();
    sheet.skipsAnimation = true;

    expect(typeof childProps.close).toBe("function");
    childProps.close();
    expect.verifySteps(["close"]);
});

test("a slot-only sheet renders, and its back slot prop routes to onBack", async () => {
    class Host extends Component {
        static components = { BottomSheet };
        static props = ["*"];
        static template = xml`
            <BottomSheet close="() => {}" onBack="() => this.onBack()">
                <t t-set-slot="default" t-slot-scope="sheet">
                    <div class="slotted"/>
                    <button class="slot-back" t-on-click="() => sheet.back()">b</button>
                </t>
            </BottomSheet>`;
        onBack() {
            expect.step("back");
        }
    }

    await mountWithCleanup(Host);
    await animationFrame();
    expect(".slotted").toHaveCount(1);

    queryOne(".slot-back").click();
    expect.verifySteps(["back"]);
});

test("a focus-trapping sheet is announced as modal, a non-trapping one is not", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }
    await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    expect(".o_bottom_sheet_sheet").toHaveAttribute("role", "dialog");
    expect(".o_bottom_sheet_sheet").toHaveAttribute("aria-modal", "true");

    await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {}, setActiveElement: false },
    });
    await animationFrame();
    expect(".o_bottom_sheet_sheet:last").not.toHaveAttribute("aria-modal");
});

test.tags("mobile");
test("a viewport change (virtual keyboard) does not dismiss the sheet", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => expect.step("closed") },
    });
    await animationFrame();
    await runAllTimers();
    expect(".sheet-child").toHaveCount(1);
    expect(sheet.state.isDismissing).toBe(false);

    patchWithCleanup(browser.visualViewport, { width: 375, height: 300 });
    sheet.updateDimensions();
    sheet.scrollRailRef.el.dispatchEvent(new Event("scroll"));
    await runAllTimers();
    await animationFrame();

    expect(sheet.state.isDismissing).toBe(false);
    expect.verifySteps([]);
});

test.tags("mobile");
test("dragging the rail below the threshold dismisses the sheet", async () => {
    class Child extends Component {
        static template = xml`<div class="sheet-child"/>`;
        static props = ["*"];
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => expect.step("closed") },
    });
    await animationFrame();
    await runAllTimers();
    expect(sheet.state.isDismissing).toBe(false);

    sheet.scrollRailRef.el.scrollTop = 0;
    sheet.scrollRailRef.el.dispatchEvent(new Event("scroll"));
    await runAllTimers();
    await animationFrame();

    expect(sheet.state.isDismissing).toBe(true);
    expect.verifySteps(["closed"]);
});

test("the sheet re-measures smaller when its content shrinks", async () => {
    defineStyle(`
        .o_bottom_sheet_sheet { min-height: var(--sheet-height); }
    `);
    class Child extends Component {
        static props = ["*"];
        static template = xml`<div class="sheet-child" t-attf-style="height: {{this.props.h}}px"/>`;
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, componentProps: { h: 600 }, close: () => {} },
    });
    await animationFrame();
    const tall = sheet.measurements.naturalHeight;
    expect(tall).toBeGreaterThan(400);

    queryOne(".sheet-child").style.height = "40px";
    sheet.updateDimensions();

    expect(sheet.measurements.naturalHeight).toBeLessThan(tall, {
        message: `natural height stayed at ${sheet.measurements.naturalHeight}`,
    });
});

test("snapping is really suppressed while the sheet is re-measured", async () => {
    class Child extends Component {
        static props = ["*"];
        static template = xml`<div class="sheet-child" style="height:300px"/>`;
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();

    const seen = [];
    patchWithCleanup(sheet, {
        measureDimensions() {
            seen.push(
                this.scrollRailRef.el?.style.getPropertyValue("scroll-snap-type"),
            );
            return super.measureDimensions();
        },
    });

    sheet.updateDimensions();

    expect(seen).toEqual(["none"], {
        message: "snapping must be off at the moment the layout is forced",
    });
    expect(
        queryOne(".o_bottom_sheet_rail").style.getPropertyValue("scroll-snap-type"),
    ).toBe("");
});

test.tags("mobile");
test("a shrinking visual viewport never sizes the sheet past it", async () => {
    class Tall extends Component {
        static template = xml`<div class="sheet-child" style="height: 900px">tall</div>`;
        static props = ["*"];
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Tall, close: () => {} },
    });
    await animationFrame();
    await runAllTimers();

    patchWithCleanup(browser.visualViewport, { width: 375, height: 300 });
    sheet.updateDimensions();
    await animationFrame();

    const sheetEl = queryOne(".o_bottom_sheet_sheet");
    const { minHeight, maxHeight } = getComputedStyle(sheetEl);
    expect(parseFloat(minHeight)).toBeLessThan(parseFloat(maxHeight) + 1);
    expect(parseFloat(maxHeight)).toBe(300);
    expect(sheetEl.getBoundingClientRect().height).toBeLessThan(301);
});

/** @param {number} height */
function resizeVisualViewport(height) {
    patchWithCleanup(browser.visualViewport, { width: 375, height });
}

test.tags("mobile");
test("the sheet grows back once the viewport does", async () => {
    class Tall extends Component {
        static template = xml`<div class="sheet-child" style="height: 900px">tall</div>`;
        static props = ["*"];
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Tall, close: () => {} },
    });
    await animationFrame();
    await runAllTimers();
    const full = sheet.measurements.initialHeight;
    expect(full).toBeGreaterThan(500);

    resizeVisualViewport(300);
    sheet.updateDimensions();
    await animationFrame();
    expect(sheet.measurements.initialHeight).toBeLessThan(full);

    resizeVisualViewport(667);
    sheet.updateDimensions();
    await animationFrame();
    expect(sheet.measurements.initialHeight).toBe(full);
});

test.tags("mobile");
test("a viewport change keeps the rail anchored to the sheet", async () => {
    class Tall extends Component {
        static template = xml`<div class="sheet-child" style="height: 900px">tall</div>`;
        static props = ["*"];
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Tall, close: () => expect.step("closed") },
    });
    await animationFrame();
    await runAllTimers();
    const rail = sheet.scrollRailRef.el;
    expect(Math.round(rail.scrollTop)).toBe(
        Math.round(sheet.measurements.initialHeight),
    );

    for (const height of [300, 667]) {
        resizeVisualViewport(height);
        sheet.updateDimensions();
        await animationFrame();
        expect(Math.round(rail.scrollTop)).toBe(
            Math.round(sheet.measurements.initialHeight),
            { message: `rail left unanchored at visual viewport ${height}` },
        );
    }

    rail.dispatchEvent(new Event("scroll"));
    await runAllTimers();
    await animationFrame();
    expect(sheet.state.isDismissing).toBe(false);
    expect.verifySteps([]);
});

const animEvent = (sel, type, name) =>
    queryOne(sel).dispatchEvent(
        new AnimationEvent(type, { bubbles: true, animationName: name }),
    );

test("the slide-in's cancellation is not the slide-out's end", async () => {
    let closed = 0;
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: AnimatedChild, close: () => closed++ },
    });
    await animationFrame();
    sheet.skipsAnimation = false;
    sheet.slideOut();
    await animationFrame();

    animEvent(".o_bottom_sheet_sheet", "animationcancel", "bottom-sheet-in");
    expect(closed).toBe(0, { message: "the cancelled slide-in closed the sheet" });

    animEvent(".o_bottom_sheet_sheet", "animationend", "bottom-sheet-out");
    expect(closed).toBe(1);
});

test("an animation the sheet does not play never closes it", async () => {
    let closed = 0;
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: AnimatedChild, close: () => closed++ },
    });
    await animationFrame();
    sheet.skipsAnimation = false;
    sheet.slideOut();
    await animationFrame();

    animEvent(".o_bottom_sheet_sheet", "animationend", "some-other-animation");
    expect(closed).toBe(0);
});

test("a cancelled slide-in does not enable snapping", async () => {
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: AnimatedChild, close: () => {} },
    });
    sheet.skipsAnimation = false;
    sheet.state.isSnappingEnabled = false;
    sheet.initializeSheet();
    await animationFrame();

    animEvent(".o_bottom_sheet_sheet", "animationcancel", "bottom-sheet-in");
    expect(sheet.state.isSnappingEnabled).toBe(false);

    animEvent(".o_bottom_sheet_sheet", "animationend", "bottom-sheet-in");
    expect(sheet.state.isSnappingEnabled).toBe(true);
});

/** @param {number} px */
async function sheetOfContentHeight(px) {
    defineStyle(`.sheet-sized-child { height: ${px}px; }`);
    class Child extends Component {
        static template = xml`<div class="sheet-sized-child"/>`;
        static props = ["*"];
    }
    const sheet = await mountWithCleanup(BottomSheet, {
        props: { component: Child, close: () => {} },
    });
    await animationFrame();
    return sheet;
}

test.tags("mobile");
test("progress reaches 1 when the sheet is fully open, however tall it is", async () => {
    const short = await sheetOfContentHeight(120);
    expect(short.measurements.naturalHeight).toBeLessThan(short.measurements.maxHeight);
    short.updateProgressValue(short.measurements.initialHeight);
    expect(short.state.progress).toBeCloseTo(1, { margin: 0.02 });
    short.updateProgressValue(0);
    expect(short.state.progress).toBeCloseTo(0, { margin: 0.02 });

    const tall = await sheetOfContentHeight(4000);
    expect(tall.measurements.naturalHeight).toBeGreaterThan(
        tall.measurements.maxHeight,
    );
    expect(tall.measurements.initialHeight).toBe(tall.measurements.maxHeight);
    tall.updateProgressValue(tall.measurements.initialHeight);
    expect(tall.state.progress).toBeCloseTo(1, { margin: 0.02 });
    tall.updateProgressValue(tall.measurements.initialHeight / 2);
    expect(tall.state.progress).toBeCloseTo(0.5, { margin: 0.02 });
});
