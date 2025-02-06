/** @odoo-module */

import { after, describe, expect, getFixture, test } from "@odoo/hoot";
import {
    clear,
    click,
    dblclick,
    drag,
    edit,
    fill,
    hover,
    keyDown,
    keyUp,
    leave,
    middleClick,
    on,
    pointerDown,
    pointerUp,
    press,
    queryOne,
    resize,
    rightClick,
    scroll,
    select,
    setInputFiles,
    setInputRange,
    uncheck,
} from "@odoo/hoot-dom";
import { advanceTime, animationFrame, mockFetch, mockTouch, mockUserAgent } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import { EventList } from "@web/../lib/hoot-dom/helpers/events";
import { mountForTest, parseUrl, waitForIframes } from "../local_helpers";

/**
 * @param {Event} ev
 */
const formatEvent = (ev) => {
    const { currentTarget, type } = ev;
    const id = currentTarget.id ? `#${currentTarget.id}` : currentTarget.tagName.toLowerCase();
    let formatted = "";

    // Mouse
    if (ev.button >= 0) {
        formatted += `:${ev.button}`;
    }
    if (ev.buttons) {
        formatted += `(${ev.buttons})`;
    }

    // Keyboard
    if (ev.key) {
        formatted += `:${ev.key}`;
    }
    if (ev.altKey) {
        formatted += `.alt`;
    }
    if (ev.ctrlKey) {
        formatted += `.ctrl`;
    }
    if (ev.metaKey) {
        formatted += `.meta`;
    }
    if (ev.shiftKey) {
        formatted += `.shift`;
    }

    // Input
    if (ev.data) {
        formatted += `:${ev.data}`;
    }

    return `${type}${formatted}@${id}`;
};

/**
 * @param {import("../../helpers/dom").Target} target
 * @param {(ev: Event) => string} [formatStep]
 */
const monitorEvents = (target, formatStep) => {
    const handleEvent = (element, type) =>
        after(
            on(element, type, (ev) => {
                const formattedStep = formatStep(ev);
                if (formattedStep) {
                    expect.step(formattedStep);
                }
            })
        );

    formatStep ||= formatEvent;

    for (const element of document.querySelectorAll(target)) {
        for (const prop in element) {
            const type = prop.match(/^on(\w+)/)?.[1];
            if (!type || BLACK_LISTED_EVENT_TYPES.includes(type)) {
                continue;
            }
            handleEvent(element, type);
        }
        for (const type of ADDITIONAL_EVENT_TYPES) {
            handleEvent(element, type);
        }
    }
};

const ADDITIONAL_EVENT_TYPES = ["focusin", "focusout"];
const BLACK_LISTED_EVENT_TYPES = ["selectionchange"];

describe(parseUrl(import.meta.url), () => {
    test("clear", async () => {
        await mountForTest(/* xml */ `<input type="text" value="Test" />`);

        expect("input").toHaveValue("Test");
        expect.verifySteps([]);

        await click("input");

        monitorEvents("input");

        await clear({ delay: 0 });

        expect("input").not.toHaveValue();
        expect.verifySteps([
            "keydown:a.ctrl@input",
            "select@input",
            "keyup:a.ctrl@input",
            "keydown:Backspace@input",
            "beforeinput@input",
            "input@input",
            "keyup:Backspace@input",
        ]);
    });

    test("clear: email", async () => {
        await mountForTest(/* xml */ `<input type="email" value="john@doe.com" />`);

        expect("input").toHaveValue("john@doe.com");

        await click("input");
        await clear();

        expect("input").toHaveValue("");
    });

    test("clear: number", async () => {
        await mountForTest(/* xml */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        await click("input");
        await clear();

        expect("input").not.toHaveValue();
    });

    test("clear: files", async () => {
        await mountForTest(/* xml */ `<input type="file" />`);
        const file = new File([""], "file.txt");

        expect("input").not.toHaveValue();

        await click("input");
        await fill(file);

        expect("input").toHaveValue([file]);

        await clear();

        expect("input").not.toHaveValue();
    });

    test("click", async () => {
        mockTouch(false);

        await mountForTest(/* xml */ `<button autofocus="" type="button">Click me</button>`);
        monitorEvents("button");

        const events = await click("button");
        const clickEvent = events.get("click");

        expect(clickEvent.pointerId).toBeGreaterThan(0);
        expect(clickEvent.pointerType).toBe("mouse");

        expect.verifySteps([
            // Hover
            "pointerover:0@button",
            "mouseover:0@button",
            "pointerenter:0@button",
            "mouseenter:0@button",
            "pointermove:0@button",
            "mousemove:0@button",
            // Click
            "pointerdown:0(1)@button",
            "mousedown:0(1)@button",
            "focus@button",
            "focusin@button",
            "pointerup:0@button",
            "mouseup:0@button",
            "click:0@button",
        ]);
    });

    test("dblclick", async () => {
        await mountForTest(/* xml */ `<button autofocus="" type="button">Click me</button>`);
        monitorEvents("button");

        await dblclick("button");

        expect.verifySteps([
            // Hover
            "pointerover:0@button",
            "mouseover:0@button",
            "pointerenter:0@button",
            "mouseenter:0@button",
            "pointermove:0@button",
            "mousemove:0@button",
            // Click 1
            "pointerdown:0(1)@button",
            "mousedown:0(1)@button",
            "focus@button",
            "focusin@button",
            "pointerup:0@button",
            "mouseup:0@button",
            "click:0@button",
            // Click 2
            "pointerdown:0(1)@button",
            "mousedown:0(1)@button",
            "pointerup:0@button",
            "mouseup:0@button",
            "click:0@button",
            // Double click event
            "dblclick:0@button",
        ]);
    });

    test("triple click", async () => {
        await mountForTest(/* xml */ `<button autofocus="" type="button">Click me</button>`);

        const allEvents = new EventList(
            // trigger 3 clicks
            await click("button"),
            await click("button"),
            await click("button")
        );

        const clickEvents = allEvents.getAll("click");
        const mouseDownEvents = allEvents.getAll("mousedown");
        const mouseUpEvents = allEvents.getAll("mouseup");
        const pointerDownEvents = allEvents.getAll("pointerdown");
        const pointerUpEvents = allEvents.getAll("pointerup");

        expect(pointerDownEvents).toHaveLength(3);
        expect(pointerDownEvents[0].detail).toBe(0);
        expect(pointerDownEvents[1].detail).toBe(0);
        expect(pointerDownEvents[2].detail).toBe(0);

        expect(mouseDownEvents).toHaveLength(3);
        expect(mouseDownEvents[0].detail).toBe(1);
        expect(mouseDownEvents[1].detail).toBe(2);
        expect(mouseDownEvents[2].detail).toBe(3);

        expect(pointerUpEvents).toHaveLength(3);
        expect(pointerUpEvents[0].detail).toBe(0);
        expect(pointerUpEvents[1].detail).toBe(0);
        expect(pointerUpEvents[2].detail).toBe(0);

        expect(mouseUpEvents).toHaveLength(3);
        expect(mouseUpEvents[0].detail).toBe(1);
        expect(mouseUpEvents[1].detail).toBe(2);
        expect(mouseUpEvents[2].detail).toBe(3);

        expect(clickEvents).toHaveLength(3);
        expect(clickEvents[0].detail).toBe(1);
        expect(clickEvents[1].detail).toBe(2);
        expect(clickEvents[2].detail).toBe(3);

        expect(allEvents.getAll("dblclick")).toHaveLength(1);

        await advanceTime(1_000);

        const events = await click("button");

        expect(events.get("click").detail).toBe(1);
    });

    test("auxclick", async () => {
        mockTouch(false);

        await mountForTest(/* xml */ `<button autofocus="" type="button">Click me</button>`);
        await hover("button");

        monitorEvents("button");

        await middleClick("button");

        expect.verifySteps([
            "pointerdown:1(4)@button",
            "mousedown:1(4)@button",
            "focus@button",
            "focusin@button",
            "pointerup:1@button",
            "mouseup:1@button",
            "auxclick:1@button",
        ]);

        await rightClick("button");

        expect.verifySteps([
            "pointerdown:2(2)@button",
            "mousedown:2(2)@button",
            "contextmenu:2(2)@button",
            "pointerup:2@button",
            "mouseup:2@button",
            "auxclick:2@button",
        ]);
    });

    test("click on disabled element", async () => {
        await mountForTest(/* xml */ `<button type="button" disabled="">Click me</button>`);

        monitorEvents("button");

        await click("button");

        expect.verifySteps([
            // Hover
            "pointerover:0@button",
            "mouseover:0@button",
            "pointerenter:0@button",
            "mouseenter:0@button",
            "pointermove:0@button",
            "mousemove:0@button",
            // Click (mouse events disabled)
            "pointerdown:0(1)@button",
            "pointerup:0@button",
        ]);
    });

    test("click on common parent", async () => {
        await mountForTest(/* xml */ `
            <main class="parent">
                <button class="first">A</button>
                <div>
                    <input class="second" />
                </div>
            </main>
        `);

        monitorEvents(".parent");
        monitorEvents(".first");
        monitorEvents(".second");

        await pointerDown(".first");
        await pointerUp(".second");

        expect.verifySteps([
            // Move to first
            "pointerover:0@button",
            "pointerover:0@main",
            "mouseover:0@button",
            "mouseover:0@main",
            "pointerenter:0@main",
            "pointerenter:0@button",
            "mouseenter:0@main",
            "mouseenter:0@button",
            "pointermove:0@button",
            "pointermove:0@main",
            "mousemove:0@button",
            "mousemove:0@main",
            // Pointer down on first
            "pointerdown:0(1)@button",
            "pointerdown:0(1)@main",
            "mousedown:0(1)@button",
            "mousedown:0(1)@main",
            "focus@button",
            "focusin@button",
            "focusin@main",
            // Move to second
            "pointermove:0(1)@button",
            "pointermove:0(1)@main",
            "mousemove:0(1)@button",
            "mousemove:0(1)@main",
            "pointerout:0(1)@button",
            "pointerout:0(1)@main",
            "mouseout:0(1)@button",
            "mouseout:0(1)@main",
            "pointerleave:0(1)@button",
            "mouseleave:0(1)@button",
            "pointerover:0(1)@input",
            "pointerover:0(1)@main",
            "mouseover:0(1)@input",
            "mouseover:0(1)@main",
            "pointerenter:0(1)@input",
            "mouseenter:0(1)@input",
            "pointermove:0(1)@input",
            "pointermove:0(1)@main",
            "mousemove:0(1)@input",
            "mousemove:0(1)@main",
            // Pointer up on second
            "pointerup:0@input",
            "pointerup:0@main",
            "mouseup:0@input",
            "mouseup:0@main",
            "click:0@main",
        ]);
    });

    test("click can be dispatched with pointer events prevented", async () => {
        await mountForTest(/* xml */ `<button type="button">Click me</button>`);

        const prevent = (ev) => ev.preventDefault();

        on("button", "pointerdown", prevent);
        on("button", "mousedown", prevent);
        on("button", "pointerup", prevent);
        on("button", "mouseup", prevent);

        await hover("button");
        monitorEvents("button");

        await click("button");

        expect.verifySteps(["pointerdown:0(1)@button", "pointerup:0@button", "click:0@button"]);
    });

    test("click: iframe", async () => {
        await mountForTest(/* xml */ `
            <button>Click me</button>
            <iframe srcdoc="&lt;button&gt;iframe button&lt;/button&gt;" />
        `);

        await waitForIframes();

        expect("button").toHaveCount(1);
        expect(":iframe button").toHaveCount(1);

        await click("button");

        expect("button").toBeFocused();
        expect(":iframe button").not.toBeFocused();

        await click(":iframe button");

        expect("button").not.toBeFocused();
        expect(":iframe button").toBeFocused();
    });

    test("drag & drop: draggable items", async () => {
        await mountForTest(/* xml */ `
            <ul>
                <li id="first-item" draggable="true">Item 1</li>
                <li id="second-item" draggable="true">Item 2</li>
                <li id="third-item" draggable="true">Item 3</li>
            </ul>
        `);

        monitorEvents("body");
        monitorEvents("li");

        // Drag & cancel
        await (await drag("#first-item")).cancel();

        expect.verifySteps([
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@body",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Cancel
            "keydown:Escape@body",
            "keyup:Escape@body",
        ]);

        // Drag & drop
        await (await drag("#first-item")).drop("#third-item");

        expect.verifySteps([
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "dragstart:0@#first-item",
            "dragstart:0@body",
            "drag:0@#first-item",
            "drag:0@body",
            "dragover:0@#first-item",
            "dragover:0@body",
            "dragleave:0@#first-item",
            "dragleave:0@body",
            // Move to third
            "dragenter:0@#third-item",
            "dragenter:0@body",
            "drag:0@#third-item",
            "drag:0@body",
            "dragover:0@#third-item",
            "dragover:0@body",
            // Drop
            "dragend:0@#third-item",
            "dragend:0@body",
        ]);

        // Drag, move & cancel
        await (await (await drag("#first-item")).moveTo("#third-item")).cancel();

        expect.verifySteps([
            // Leave third
            "pointermove:0@#third-item",
            "pointermove:0@body",
            "mousemove:0@#third-item",
            "mousemove:0@body",
            "pointerout:0@#third-item",
            "pointerout:0@body",
            "mouseout:0@#third-item",
            "mouseout:0@body",
            "pointerleave:0@#third-item",
            "mouseleave:0@#third-item",
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "dragstart:0@#first-item",
            "dragstart:0@body",
            "drag:0@#first-item",
            "drag:0@body",
            "dragover:0@#first-item",
            "dragover:0@body",
            "dragleave:0@#first-item",
            "dragleave:0@body",
            // Move to third
            "dragenter:0@#third-item",
            "dragenter:0@body",
            "drag:0@#third-item",
            "drag:0@body",
            "dragover:0@#third-item",
            "dragover:0@body",
            // Cancel
            "keydown:Escape@body",
            "keyup:Escape@body",
        ]);

        // Drag, move & drop
        await (await (await drag("#first-item")).moveTo("#third-item")).drop();

        expect.verifySteps([
            // Leave third
            "pointermove:0@#third-item",
            "pointermove:0@body",
            "mousemove:0@#third-item",
            "mousemove:0@body",
            "pointerout:0@#third-item",
            "pointerout:0@body",
            "mouseout:0@#third-item",
            "mouseout:0@body",
            "pointerleave:0@#third-item",
            "mouseleave:0@#third-item",
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "dragstart:0@#first-item",
            "dragstart:0@body",
            "drag:0@#first-item",
            "drag:0@body",
            "dragover:0@#first-item",
            "dragover:0@body",
            "dragleave:0@#first-item",
            "dragleave:0@body",
            // Move to third
            "dragenter:0@#third-item",
            "dragenter:0@body",
            "drag:0@#third-item",
            "drag:0@body",
            "dragover:0@#third-item",
            "dragover:0@body",
            // Drop
            "dragend:0@#third-item",
            "dragend:0@body",
        ]);

        // Drag, move & drop (different target)
        await (await (await drag("#first-item")).moveTo("#second-item")).drop("#third-item");

        expect.verifySteps([
            // Leave third
            "pointermove:0@#third-item",
            "pointermove:0@body",
            "mousemove:0@#third-item",
            "mousemove:0@body",
            "pointerout:0@#third-item",
            "pointerout:0@body",
            "mouseout:0@#third-item",
            "mouseout:0@body",
            "pointerleave:0@#third-item",
            "mouseleave:0@#third-item",
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "dragstart:0@#first-item",
            "dragstart:0@body",
            "drag:0@#first-item",
            "drag:0@body",
            "dragover:0@#first-item",
            "dragover:0@body",
            "dragleave:0@#first-item",
            "dragleave:0@body",
            // Move to second
            "dragenter:0@#second-item",
            "dragenter:0@body",
            "drag:0@#second-item",
            "drag:0@body",
            "dragover:0@#second-item",
            "dragover:0@body",
            // Leave second
            "drag:0@#second-item",
            "drag:0@body",
            "dragover:0@#second-item",
            "dragover:0@body",
            "dragleave:0@#second-item",
            "dragleave:0@body",
            // Move to third
            "dragenter:0@#third-item",
            "dragenter:0@body",
            "drag:0@#third-item",
            "drag:0@body",
            "dragover:0@#third-item",
            "dragover:0@body",
            // Drop
            "dragend:0@#third-item",
            "dragend:0@body",
        ]);
    });

    test("drag & drop: non-draggable items", async () => {
        await mountForTest(/* xml */ `
            <ul>
                <li id="first-item">Item 1</li>
                <li id="second-item">Item 2</li>
                <li id="third-item">Item 3</li>
            </ul>
        `);

        monitorEvents("body");
        monitorEvents("li");

        // Drag & cancel
        await (await drag("#first-item")).cancel();

        expect.verifySteps([
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@body",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Cancel
            "keydown:Escape@body",
            "keyup:Escape@body",
        ]);

        // Drag & drop
        await (await drag("#first-item")).drop("#third-item");

        expect.verifySteps([
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "pointermove:0(1)@#first-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#first-item",
            "mousemove:0(1)@body",
            "pointerout:0(1)@#first-item",
            "pointerout:0(1)@body",
            "mouseout:0(1)@#first-item",
            "mouseout:0(1)@body",
            "pointerleave:0(1)@#first-item",
            "mouseleave:0(1)@#first-item",
            // Move to third
            "pointerover:0(1)@#third-item",
            "pointerover:0(1)@body",
            "mouseover:0(1)@#third-item",
            "mouseover:0(1)@body",
            "pointerenter:0(1)@#third-item",
            "mouseenter:0(1)@#third-item",
            "pointermove:0(1)@#third-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#third-item",
            "mousemove:0(1)@body",
            // Drop
            "pointerup:0@#third-item",
            "pointerup:0@body",
            "mouseup:0@#third-item",
            "mouseup:0@body",
            "click:0@body",
        ]);

        // Drag, move & cancel
        await (await (await drag("#first-item")).moveTo("#third-item")).cancel();

        expect.verifySteps([
            // Leave third
            "pointermove:0@#third-item",
            "pointermove:0@body",
            "mousemove:0@#third-item",
            "mousemove:0@body",
            "pointerout:0@#third-item",
            "pointerout:0@body",
            "mouseout:0@#third-item",
            "mouseout:0@body",
            "pointerleave:0@#third-item",
            "mouseleave:0@#third-item",
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "pointermove:0(1)@#first-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#first-item",
            "mousemove:0(1)@body",
            "pointerout:0(1)@#first-item",
            "pointerout:0(1)@body",
            "mouseout:0(1)@#first-item",
            "mouseout:0(1)@body",
            "pointerleave:0(1)@#first-item",
            "mouseleave:0(1)@#first-item",
            // Move to third
            "pointerover:0(1)@#third-item",
            "pointerover:0(1)@body",
            "mouseover:0(1)@#third-item",
            "mouseover:0(1)@body",
            "pointerenter:0(1)@#third-item",
            "mouseenter:0(1)@#third-item",
            "pointermove:0(1)@#third-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#third-item",
            "mousemove:0(1)@body",
            // Cancel
            "keydown:Escape@body",
            "keyup:Escape@body",
        ]);

        // Drag, move & drop
        await (await (await drag("#first-item")).moveTo("#third-item")).drop();

        expect.verifySteps([
            // Leave third
            "pointermove:0@#third-item",
            "pointermove:0@body",
            "mousemove:0@#third-item",
            "mousemove:0@body",
            "pointerout:0@#third-item",
            "pointerout:0@body",
            "mouseout:0@#third-item",
            "mouseout:0@body",
            "pointerleave:0@#third-item",
            "mouseleave:0@#third-item",
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "pointermove:0(1)@#first-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#first-item",
            "mousemove:0(1)@body",
            "pointerout:0(1)@#first-item",
            "pointerout:0(1)@body",
            "mouseout:0(1)@#first-item",
            "mouseout:0(1)@body",
            "pointerleave:0(1)@#first-item",
            "mouseleave:0(1)@#first-item",
            // Move to third
            "pointerover:0(1)@#third-item",
            "pointerover:0(1)@body",
            "mouseover:0(1)@#third-item",
            "mouseover:0(1)@body",
            "pointerenter:0(1)@#third-item",
            "mouseenter:0(1)@#third-item",
            "pointermove:0(1)@#third-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#third-item",
            "mousemove:0(1)@body",
            // Drop
            "pointerup:0@#third-item",
            "pointerup:0@body",
            "mouseup:0@#third-item",
            "mouseup:0@body",
            "click:0@body",
            "dblclick:0@body",
        ]);

        // Drag, move & drop (different target)
        await (await (await drag("#first-item")).moveTo("#second-item")).drop("#third-item");

        expect.verifySteps([
            // Leave third
            "pointermove:0@#third-item",
            "pointermove:0@body",
            "mousemove:0@#third-item",
            "mousemove:0@body",
            "pointerout:0@#third-item",
            "pointerout:0@body",
            "mouseout:0@#third-item",
            "mouseout:0@body",
            "pointerleave:0@#third-item",
            "mouseleave:0@#third-item",
            // Move to first
            "pointerover:0@#first-item",
            "pointerover:0@body",
            "mouseover:0@#first-item",
            "mouseover:0@body",
            "pointerenter:0@#first-item",
            "mouseenter:0@#first-item",
            "pointermove:0@#first-item",
            "pointermove:0@body",
            "mousemove:0@#first-item",
            "mousemove:0@body",
            // Drag first
            "pointerdown:0(1)@#first-item",
            "pointerdown:0(1)@body",
            "mousedown:0(1)@#first-item",
            "mousedown:0(1)@body",
            // Leave first
            "pointermove:0(1)@#first-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#first-item",
            "mousemove:0(1)@body",
            "pointerout:0(1)@#first-item",
            "pointerout:0(1)@body",
            "mouseout:0(1)@#first-item",
            "mouseout:0(1)@body",
            "pointerleave:0(1)@#first-item",
            "mouseleave:0(1)@#first-item",
            // Move to second
            "pointerover:0(1)@#second-item",
            "pointerover:0(1)@body",
            "mouseover:0(1)@#second-item",
            "mouseover:0(1)@body",
            "pointerenter:0(1)@#second-item",
            "mouseenter:0(1)@#second-item",
            "pointermove:0(1)@#second-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#second-item",
            "mousemove:0(1)@body",
            // Leave second
            "pointermove:0(1)@#second-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#second-item",
            "mousemove:0(1)@body",
            "pointerout:0(1)@#second-item",
            "pointerout:0(1)@body",
            "mouseout:0(1)@#second-item",
            "mouseout:0(1)@body",
            "pointerleave:0(1)@#second-item",
            "mouseleave:0(1)@#second-item",
            // Move to third
            "pointerover:0(1)@#third-item",
            "pointerover:0(1)@body",
            "mouseover:0(1)@#third-item",
            "mouseover:0(1)@body",
            "pointerenter:0(1)@#third-item",
            "mouseenter:0(1)@#third-item",
            "pointermove:0(1)@#third-item",
            "pointermove:0(1)@body",
            "mousemove:0(1)@#third-item",
            "mousemove:0(1)@body",
            // Drop
            "pointerup:0@#third-item",
            "pointerup:0@body",
            "mouseup:0@#third-item",
            "mouseup:0@body",
            "click:0@body",
        ]);
    });

    test("drag & drop: touch environment", async () => {
        mockTouch(true);

        await mountForTest(/* xml */ `
            <ul>
                <li id="first-item">Item 1</li>
                <li id="second-item">Item 2</li>
                <li id="third-item">Item 3</li>
            </ul>
        `);

        const firstItem = queryOne("#first-item");
        const events = await (await drag("#first-item")).drop("#third-item");
        const touchEvents = events.getAll((ev) => ev.type.startsWith("touch"));

        expect(touchEvents.map((e) => e.target)).toEqual(
            [
                firstItem, // start
                firstItem, // move (on first)
                firstItem, // move (on last)
                firstItem, // end
            ],
            { message: "touch events should all target the same element" }
        );

        const [touchStart, touchMove, , touchEnd] = touchEvents;

        expect(touchStart).not.toInclude("clientX");
        expect(touchStart).not.toInclude("clientY");
        expect(touchStart.touches).toHaveLength(1);

        expect(touchMove.touches).toHaveLength(1);

        expect(touchEnd).not.toInclude("clientX");
        expect(touchEnd).not.toInclude("clientY");
        expect(touchEnd.touches).toHaveLength(0);
    });

    test("fill: text", async () => {
        await mountForTest(/* xml */ `<input type="text" value="" />`);

        expect("input").not.toHaveValue();
        expect.verifySteps([]);

        await click("input");

        monitorEvents("input");

        await fill("Test value");

        expect("input").toHaveValue("Test value");
        expect.verifySteps([
            ...[..."Test value"].flatMap((char) => {
                let key = char.toLowerCase();
                if (char !== char.toLowerCase()) {
                    key += ".shift";
                }
                return [
                    `keydown:${key}@input`,
                    `beforeinput:${char}@input`,
                    `input:${char}@input`,
                    `keyup:${key}@input`,
                ];
            }),
        ]);
    });

    test("fill: text with previous value", async () => {
        await mountForTest(/* xml */ `<input type="text" value="Test" />`);

        expect("input").toHaveValue("Test");

        await click("input");
        await fill(" value");

        expect("input").toHaveValue("Test value");
    });

    test("fill: number", async () => {
        await mountForTest(/* xml */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        await click("input");
        await fill(42);

        expect("input").toHaveValue(42);
    });

    test("fill: email", async () => {
        await mountForTest(/* xml */ `<input type="email" />`);

        expect("input").not.toHaveValue();

        await click("input");
        await fill("john@doe.com");

        expect("input").toHaveValue("john@doe.com");
    });

    test("edit on empty value", async () => {
        await mountForTest(/* xml */ `<input type="text" />`);

        await click("input");

        monitorEvents("input");

        expect("input").not.toHaveValue();

        await edit("test value");

        expect("input").toHaveValue("test value");
        expect.verifySteps([
            ...[..."test value"].flatMap((char) => [
                `keydown:${char}@input`,
                `beforeinput:${char}@input`,
                `input:${char}@input`,
                `keyup:${char}@input`,
            ]),
        ]);

        await click(getFixture());

        expect.verifySteps([
            // Pointer out
            "pointermove:0@input",
            "mousemove:0@input",
            "pointerout:0@input",
            "mouseout:0@input",
            "pointerleave:0@input",
            "mouseleave:0@input",
            // Change
            "blur@input",
            "change@input",
            "focusout@input",
        ]);
    });

    test("edit on existing value", async () => {
        await mountForTest(/* xml */ `<input type="text" value="Test" />`);

        await click("input");
        await animationFrame();

        monitorEvents("input");

        expect("input").toHaveValue("Test");

        await edit(" value");
        await animationFrame();

        expect("input").toHaveValue(" value");
        expect.verifySteps([
            // Clear
            "keydown:a.ctrl@input",
            "select@input",
            "keyup:a.ctrl@input",
            "keydown:Backspace@input",
            "beforeinput@input",
            "input@input",
            "keyup:Backspace@input",
            // Fill
            ...[..." value"].flatMap((char) => [
                `keydown:${char}@input`,
                `beforeinput:${char}@input`,
                `input:${char}@input`,
                `keyup:${char}@input`,
            ]),
            "select@input",
        ]);
    });

    test("edit with dirty value and blur", async () => {
        await mountForTest(/* xml */ `
            <input type="text" />
            <button>Diversion</button>
        `);
        await click("input");
        await edit("test value");

        monitorEvents("input");
        monitorEvents("button");

        await click("button");

        expect.verifySteps([
            // Move to button
            "pointermove:0@input",
            "mousemove:0@input",
            "pointerout:0@input",
            "mouseout:0@input",
            "pointerleave:0@input",
            "mouseleave:0@input",
            "pointerover:0@button",
            "mouseover:0@button",
            "pointerenter:0@button",
            "mouseenter:0@button",
            "pointermove:0@button",
            "mousemove:0@button",
            // Click on button
            "pointerdown:0(1)@button",
            "mousedown:0(1)@button",
            "change@input",
            "blur@input",
            "focusout@input",
            "focus@button",
            "focusin@button",
            "pointerup:0@button",
            "mouseup:0@button",
            "click:0@button",
        ]);
    });

    test("edit with dirty value and confirm with enter", async () => {
        await mountForTest(/* xml */ `
            <input type="text" />
            <button>Diversion</button>
        `);
        await click("input");
        await edit("test value");

        monitorEvents("input");

        await press("Enter");

        expect.verifySteps(["keydown:Enter@input", "change@input", "keyup:Enter@input"]);
    });

    test("edit: iframe", async () => {
        await mountForTest(/* xml */ `
            <input type="text" />
            <iframe srcdoc="&lt;input type='text' /&gt;" />
        `);

        await waitForIframes();

        expect("input").toHaveCount(1);
        expect(":iframe input").toHaveCount(1);

        on("input", "change", () => expect.step("top:change"));
        on(":iframe input", "change", () => expect.step("iframe:change"));

        await click("input");
        await edit("abc");

        expect.verifySteps([]);
        expect("input").toHaveValue("abc");
        expect(":iframe input").toHaveValue("");

        await click(":iframe input");
        await edit("def");

        expect.verifySteps(["top:change"]);
        expect("input").toHaveValue("abc");
        expect(":iframe input").toHaveValue("def");

        await click(":iframe body");
        expect.verifySteps(["iframe:change"]);
    });

    test("setInputFiles: single file", async () => {
        await mountForTest(/* xml */ `<input type="file" />`);
        const file1 = new File([""], "file1.txt");
        const file2 = new File([""], "file2.txt");

        expect("input").not.toHaveValue();

        await click("input");
        await setInputFiles(file1);

        expect("input").toHaveValue(/file1\.txt/);
        expect("input").toHaveValue([file1]);

        await click("input");
        await setInputFiles(file2);

        expect("input").toHaveValue(/file2\.txt/);
        expect("input").toHaveValue([file2]);
    });

    test("setInputFiles: multiple files", async () => {
        await mountForTest(/* xml */ `<input type="file" multiple="multiple" />`);
        const file1 = new File([""], "file1.txt");
        const file2 = new File([""], "file2.txt");

        expect("input").not.toHaveValue();

        await click("input");
        await setInputFiles(file1);

        expect("input").toHaveValue(/file1\.txt/);
        expect("input").toHaveValue([file1]);

        await click("input");
        await setInputFiles([file1, file2]);

        expect("input").toHaveValue([file1, file2]);
    });

    test("setInputFiles: hidden input with label", async () => {
        await mountForTest(/* xml */ `
            <label for="file-input">Label</label>
            <input id="file-input" style="display: none" type="file" />
        `);

        expect("input").not.toBeVisible();
        expect("input").not.toHaveValue();
        expect("label").toBeVisible();

        await click("label");
        await setInputFiles(new File([""], "file.txt"));

        expect("input").toHaveValue(/file\.txt/);
    });

    test("setInputFiles: hidden input with programmatic click", async () => {
        await mountForTest(/* xml */ `
            <button>upload</button>
            <input style="display: none" type="file" />
        `);

        on("button", "click", () => queryOne("input").click());

        expect("input").not.toBeVisible();
        expect("input").not.toHaveValue();
        expect("button").toBeVisible();

        await click("button");
        await setInputFiles(new File([""], "file.txt"));

        expect("input").toHaveValue(/file\.txt/);
    });

    test("setInputRange: basic case and events", async () => {
        await mountForTest(/* xml */ `<input type="range" min="10" max="40" />`);

        monitorEvents("input");

        await setInputRange("input", 30);

        expect("input").toHaveValue(30);
        expect.verifySteps([
            // Hover input
            "pointerover:0@input",
            "mouseover:0@input",
            "pointerenter:0@input",
            "mouseenter:0@input",
            "pointermove:0@input",
            "mousemove:0@input",
            // Pointer down
            "pointerdown:0(1)@input",
            "mousedown:0(1)@input",
            "focus@input",
            "focusin@input",
            // Set range
            "input@input",
            "change@input",
            // Pointer up
            "pointerup:0@input",
            "mouseup:0@input",
            "click:0@input",
        ]);
    });

    test("setInputRange: out of min and max values", async () => {
        await mountForTest(/* xml */ `<input type="range" min="10" max="40" />`);

        await setInputRange("input", 5);

        expect("input").toHaveValue(10);

        await setInputRange("input", 50);

        expect("input").toHaveValue(40);
    });

    test("hover", async () => {
        await mountForTest(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        await hover("button");

        expect.verifySteps([
            "pointerover:0@button",
            "mouseover:0@button",
            "pointerenter:0@button",
            "mouseenter:0@button",
            "pointermove:0@button",
            "mousemove:0@button",
        ]);

        await hover("button");

        expect.verifySteps(["pointermove:0@button", "mousemove:0@button"]);
    });

    test("leave", async () => {
        await mountForTest(/* xml */ `<button type="button">Click me</button>`);

        await hover("button");

        monitorEvents("button");

        await leave();

        expect.verifySteps([
            "pointermove:0@button",
            "mousemove:0@button",
            "pointerout:0@button",
            "mouseout:0@button",
            "pointerleave:0@button",
            "mouseleave:0@button",
        ]);
    });

    test("keyDown", async () => {
        await mountForTest(/* xml */ `<input type="text" />`);

        await click("input");

        monitorEvents("input");

        await keyDown("a");

        expect.verifySteps(["keydown:a@input", "beforeinput:a@input", "input:a@input"]);

        await keyUp("a");

        expect("input").toHaveValue("a");
        expect.verifySteps(["keyup:a@input"]);
    });

    test("multiple keyDown should be flagged as repeated", async () => {
        let events;

        await mountForTest(/* xml */ `<input type="text" />`);

        await click("input");

        monitorEvents("input");

        events = await keyDown("Enter");
        expect(events.get("keydown").repeat).toBe(false);

        events = await keyDown("Enter");
        expect(events.get("keydown").repeat).toBe(true);

        events = await keyDown("Enter");
        expect(events.get("keydown").repeat).toBe(true);

        events = await keyDown("Escape");
        expect(events.get("keydown").repeat).toBe(false);

        events = await keyDown("Enter");
        expect(events.get("keydown").repeat).toBe(false);

        events = await keyUp("Enter");
        expect(events.get("keydown")).toBe(null);

        events = await keyDown("Enter");
        expect(events.get("keydown").repeat).toBe(false);

        events = await keyDown("Enter");
        expect(events.get("keydown").repeat).toBe(true);

        expect.verifySteps([
            "keydown:Enter@input",
            "keydown:Enter@input",
            "keydown:Enter@input",
            "keydown:Escape@input",
            "keydown:Enter@input",
            "keyup:Enter@input",
            "keydown:Enter@input",
            "keydown:Enter@input",
        ]);
    });

    test("pointerDown", async () => {
        await mountForTest(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        await pointerDown("button");

        expect.verifySteps([
            // Pointer enter on button
            "pointerover:0@button",
            "mouseover:0@button",
            "pointerenter:0@button",
            "mouseenter:0@button",
            "pointermove:0@button",
            "mousemove:0@button",
            // Pointer down
            "pointerdown:0(1)@button",
            "mousedown:0(1)@button",
            "focus@button",
            "focusin@button",
        ]);

        await pointerUp("button");

        expect.verifySteps(["pointerup:0@button", "mouseup:0@button", "click:0@button"]);
    });

    test("press key on text input", async () => {
        await mountForTest(/* xml */ `<input type="text" />`);

        await click("input");

        monitorEvents("input");

        await press("a");

        expect("input").toHaveValue("a");
        expect.verifySteps([
            "keydown:a@input",
            "beforeinput:a@input",
            "input:a@input",
            "keyup:a@input",
        ]);
    });

    test("press key on number input", async () => {
        await mountForTest(/* xml */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        await click("input");
        await press("4");

        expect("input").toHaveValue(4);

        await press("2");

        expect("input").toHaveValue(42);
    });

    test("press arrow keys on input", async () => {
        await mountForTest(/* xml */ `<input value="value" />`);

        await click("input");

        expect("input").toHaveProperty("selectionStart", 5);
        expect("input").toHaveProperty("selectionEnd", 5);

        await press("left");

        expect("input").toHaveProperty("selectionStart", 4);
        expect("input").toHaveProperty("selectionEnd", 4);

        await press("left");
        await press("left");
        await press("right");

        expect("input").toHaveProperty("selectionStart", 3);
        expect("input").toHaveProperty("selectionEnd", 3);

        await press(["control", "a"]);

        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 5);

        await press("right");

        expect("input").toHaveProperty("selectionStart", 5);
        expect("input").toHaveProperty("selectionEnd", 5);

        await press(["ctrl", "a"]);
        await press("down");

        expect("input").toHaveProperty("selectionStart", 5);
        expect("input").toHaveProperty("selectionEnd", 5);

        await press(["ctrl", "a"]);
        await press("left");

        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 0);

        await press(["ctrl", "a"]);
        await press("up");

        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 0);
    });

    test("insert character updates selection", async () => {
        await mountForTest(/* xml */ `<input value="abc" />`);

        await click("input");

        const input = queryOne("input");
        input.selectionStart = 0;
        input.selectionEnd = 3;

        await press("d");

        expect("input").toHaveValue("d");
        expect("input").toHaveProperty("selectionStart", 1);
        expect("input").toHaveProperty("selectionEnd", 1);

        await press("f");

        expect("input").toHaveValue("df");
        expect("input").toHaveProperty("selectionStart", 2);
        expect("input").toHaveProperty("selectionEnd", 2);

        input.selectionStart = 1;
        input.selectionEnd = 1;

        await press("e");

        expect("input").toHaveValue("def");
        expect("input").toHaveProperty("selectionStart", 2);
        expect("input").toHaveProperty("selectionEnd", 2);
    });

    test("press 'Enter' on form input", async () => {
        await mountForTest(/* xml */ `
            <form t-on-submit.prevent="">
                <input type="text" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("input");

        expect("input").not.toBeFocused();

        await press("Tab");
        await animationFrame();

        expect("input").toBeFocused();

        await press("Enter");
        await animationFrame();

        expect.verifySteps([
            // Tab
            "focus@input",
            "focusin@input",
            "focusin@form",
            "select@input",
            "select@form",
            // Enter
            "keydown:Enter@input",
            "keydown:Enter@form",
            "submit@form",
            "keyup:Enter@input",
            "keyup:Enter@form",
        ]);
    });

    test("press 'Enter' on form button", async () => {
        await mountForTest(/* xml */ `
            <form t-on-submit.prevent="">
                <button type="button" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("button");

        expect("button").not.toBeFocused();

        await press("Tab");

        expect("button").toBeFocused();

        await press("Enter");

        expect.verifySteps([
            // Tab
            "focus@button",
            "focusin@button",
            "focusin@form",
            // Enter
            "keydown:Enter@button",
            "keydown:Enter@form",
            "click:0@button",
            "click:0@form",
            "keyup:Enter@button",
            "keyup:Enter@form",
        ]);
    });

    test("press 'Enter' on form submit button", async () => {
        await mountForTest(/* xml */ `
            <form t-on-submit.prevent="">
                <button type="submit" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("button");

        expect("button").not.toBeFocused();

        await press("Tab");

        expect("button").toBeFocused();

        await press("Enter");

        expect.verifySteps([
            // Tab
            "focus@button",
            "focusin@button",
            "focusin@form",
            // Enter
            "keydown:Enter@button",
            "keydown:Enter@form",
            "submit@form",
            "keyup:Enter@button",
            "keyup:Enter@form",
        ]);
    });

    test("form submissions are redirected to mocked fetch", async () => {
        await mountForTest(/* xml */ `
            <form action="/submit/url" method="POST">
                <input type="hidden" name="csrf_token" value="CSRF_TOKEN_VALUE" />
                <input type="text" name="name" />
                <input type="number" name="experience" />
                <input type="file" name="picture" />
            </form>
        `);

        mockFetch((url, { body, method }) => {
            expect.step(new URL(url).pathname);

            expect(method).toBe("post");
            expect(body).toBeInstanceOf(FormData);
            expect(body.get("csrf_token")).toBe("CSRF_TOKEN_VALUE");
            expect(body.get("name")).toBe("Pierre");
            expect(body.get("experience")).toBe("3");
            expect(body.get("picture").name).toBe("/picture_128.png");
        });

        await click("[name=name]");
        await fill("Pierre");

        await press("tab");
        await fill(3);

        await press("tab");
        await setInputFiles(new File([], "/picture_128.png"));

        expect.verifySteps([]);

        monitorEvents("form");

        // Trigger submit
        await press("enter");

        expect.verifySteps([
            "keydown:Enter@form",
            "submit@form",
            "formdata@form",
            "/submit/url",
            "keyup:Enter@form",
        ]);
    });

    test("press 'Space' on checkbox input", async () => {
        await mountForTest(/* xml */ `<input type="checkbox" checked="" />`);

        expect("input").toHaveProperty("checked", true);

        await uncheck("input"); // true -> false

        expect("input").toHaveProperty("checked", false);

        monitorEvents("input");

        await press(" "); // false -> true

        expect("input").toHaveProperty("checked", true);
        expect.verifySteps([
            // Key press
            "keydown: @input",
            "beforeinput: @input",
            "input: @input",
            "keyup: @input",
            // Click triggered by key press
            "click:0@input",
            "input@input",
            "change@input",
        ]);
    });

    test("press 'Backspace' on number input", async () => {
        await mountForTest(/* xml */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        await click("input");
        await press("Backspace");

        expect("input").toHaveValue(42);

        await press("Backspace");

        expect("input").toHaveValue(4);
    });

    test("press 'Enter' on textarea", async () => {
        await mountForTest(/* xml */ `<textarea t-att-value="'aaa'" />`);

        expect("textarea").toHaveValue("aaa");

        await click("textarea");
        await press("Enter");

        expect("textarea").toHaveValue("aaa\n");
    });

    test("special keys modifiers: Windows", async () => {
        mockUserAgent("windows");

        await mountForTest(/* xml */ `<input />`);

        await click("input");

        monitorEvents("input");

        await press("alt");

        expect.verifySteps(["keydown:Alt.alt@input", "keyup:Alt.alt@input"]);

        await press("ctrl");

        expect.verifySteps(["keydown:Control.ctrl@input", "keyup:Control.ctrl@input"]);

        await press("meta");

        expect.verifySteps(["keydown:Meta.meta@input", "keyup:Meta.meta@input"]);

        await press("shift");

        expect.verifySteps(["keydown:Shift.shift@input", "keyup:Shift.shift@input"]);
    });

    test("special keys modifiers: Mac", async () => {
        mockUserAgent("mac");

        await mountForTest(/* xml */ `<input />`);

        await click("input");

        monitorEvents("input");

        await press("alt");

        expect.verifySteps(["keydown:Alt.alt@input", "keyup:Alt.alt@input"]);

        await press("ctrl");

        expect.verifySteps(["keydown:Control.ctrl@input", "keyup:Control.ctrl@input"]);

        await press("meta");

        expect.verifySteps(["keydown:Meta.meta@input", "keyup:Meta.meta@input"]);

        await press("shift");

        expect.verifySteps(["keydown:Shift.shift@input", "keyup:Shift.shift@input"]);
    });

    test("compose shift, alt and control and a key", async () => {
        await mountForTest(/* xml */ `<input />`);

        await click("input");

        monitorEvents("input");

        await press(["ctrl", "b"]);

        expect.verifySteps([
            "keydown:Control.ctrl@input",
            "keydown:b.ctrl@input",
            "keyup:b.ctrl@input",
            "keyup:Control.ctrl@input",
        ]);

        await press(["shift", "b"]);

        expect.verifySteps([
            "keydown:Shift.shift@input",
            "keydown:b.shift@input",
            "beforeinput:B@input",
            "input:B@input",
            "keyup:b.shift@input",
            "keyup:Shift.shift@input",
        ]);

        await press(["Alt", "Control", "b"]);

        expect.verifySteps([
            "keydown:Alt.alt@input",
            "keydown:Control.alt.ctrl@input",
            "keydown:b.alt.ctrl@input",
            "keyup:b.alt.ctrl@input",
            "keyup:Control.alt.ctrl@input",
            "keyup:Alt.alt@input",
        ]);
    });

    test("scroll", async () => {
        await mountForTest(/* xml */ `
            <div class="scrollable" style="height: 200px; width: 200px; overflow: auto;">
                <div style="height: 2000px; width: 2000px;"></div>
            </div>
        `);

        monitorEvents(".scrollable");

        await scroll(".scrollable", { top: 500 });
        await animationFrame();

        expect(".scrollable").toHaveProperty("scrollTop", 500);
        expect(".scrollable").toHaveProperty("scrollLeft", 0);
        expect.verifySteps(["wheel:0@div", "scroll@div", "scrollend@div"]);

        await scroll(".scrollable", { left: 1200 });
        await animationFrame();

        expect(".scrollable").toHaveProperty("scrollTop", 500);
        expect(".scrollable").toHaveProperty("scrollLeft", 1200);
        expect.verifySteps(["wheel:0@div", "scroll@div", "scrollend@div"]);
    });

    test("resize", async () => {
        await mountForTest(/* xml */ `
            <div class="resizable" style="height: 200px; width: 200px; overflow: auto;"/>
        `);

        const { innerHeight } = window;

        after(on(window, "resize", () => expect.step("resize@window")));

        await resize({ width: 300 });

        expect(window.innerWidth).toBe(300);
        expect(window.innerHeight).toBe(innerHeight);

        expect.verifySteps(["resize@window"]);

        await resize({ height: 264 });

        expect(window.innerWidth).toBe(300);
        expect(window.innerHeight).toBe(264);

        expect.verifySteps(["resize@window"]);
    });

    test("select", async () => {
        await mountForTest(/* xml */ `
            <select>
                <option value="a">A</option>
                <option value="b">B</option>
                <option value="c">C</option>
            </select>
        `);

        expect("select").toHaveValue("a"); // default to first option
        expect.verifySteps([]);

        await click("select");

        monitorEvents("select");

        await select("b");

        expect("select").toHaveValue("b");
        expect.verifySteps(["change@select"]);
    });

    test("can trigger synthetic event handlers", async () => {
        await mountForTest(
            class extends Component {
                static props = {};
                static template = xml`
                    <button t-on-click.synthetic="onClick">Click me</button>
                `;

                onClick() {
                    expect.step("click");
                }
            }
        );

        await click("button");

        expect.verifySteps(["click"]);
    });

    test("synthetic event handlers are not cleaned up between tests", async () => {
        await mountForTest(
            class extends Component {
                static props = {};
                static template = xml`
                    <button t-on-click.synthetic="onClick">Click me</button>
                `;

                onClick() {
                    expect.step("clack");
                }
            }
        );

        await click("button");

        expect.verifySteps(["clack"]);
    });
});
