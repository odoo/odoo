/** @odoo-module */

import { after, describe, expect, getFixture, mountOnFixture, test } from "@odoo/hoot";
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
    on,
    pointerDown,
    pointerUp,
    press,
    queryOne,
    resize,
    scroll,
    select,
    setInputFiles,
    setInputRange,
    uncheck,
} from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { mockUserAgent } from "../../mock/navigator";
import { advanceTime, animationFrame } from "../../mock/time";
import { parseUrl, waitForIframes } from "../local_helpers";

/**
 * @param {KeyboardEvent} ev
 */
const formatKeyBoardEvent = (ev) =>
    `${ev.type}${ev.key ? `:${ev.key}` : ""}${ev.altKey ? ".alt" : ""}${ev.ctrlKey ? ".ctrl" : ""}${
        ev.metaKey ? ".meta" : ""
    }${ev.shiftKey ? ".shift" : ""}`;

/**
 * @param {import("../../helpers/dom").Target} target
 * @param {(ev: Event) => string} [formatStep]
 */
const monitorEvents = (target, formatStep) => {
    const handleEvent = (element, type) => {
        const passive = type !== "submit";
        const off = on(
            element,
            type,
            (ev) => {
                const step = formatStep(ev);
                if (step) {
                    expect.step(formatStep(ev));
                }
                if (!passive) {
                    ev.preventDefault();
                }
            },
            { passive }
        );
        after(off);
    };

    formatStep ||= (ev) => `${ev.currentTarget.tagName.toLowerCase()}.${ev.type}`;

    for (const element of document.querySelectorAll(target)) {
        for (const prop in element) {
            const type = prop.match(/^on(\w+)/)?.[1];
            if (!type) {
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

describe(parseUrl(import.meta.url), () => {
    test("clear", async () => {
        await mountOnFixture(/* xml */ `<input type="text" value="Test" />`);

        expect("input").toHaveValue("Test");
        expect.verifySteps([]);

        click("input");

        monitorEvents("input");

        clear();

        expect("input").not.toHaveValue();
        expect.verifySteps([
            "input.keydown",
            "input.select",
            "input.keyup",
            "input.keydown",
            "input.beforeinput",
            "input.input",
            "input.keyup",
        ]);
    });

    test("clear: email", async () => {
        await mountOnFixture(/* xml */ `<input type="email" value="john@doe.com" />`);

        expect("input").toHaveValue("john@doe.com");

        click("input");
        clear();

        expect("input").toHaveValue("");
    });

    test("clear: number", async () => {
        await mountOnFixture(/* xml */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        click("input");
        clear();

        expect("input").not.toHaveValue();
    });

    test("clear: files", async () => {
        await mountOnFixture(/* xml */ `<input type="file" />`);
        const file = new File([""], "file.txt");

        expect("input").not.toHaveValue();

        click("input");
        fill(file);

        expect("input").toHaveValue([file]);

        clear();

        expect("input").not.toHaveValue();
    });

    test("click", async () => {
        await mountOnFixture(/* xml */ `<button autofocus="" type="button">Click me</button>`);
        monitorEvents("button");

        click("button");

        expect.verifySteps([
            // Hover
            "button.pointerover",
            "button.mouseover",
            "button.pointerenter",
            "button.mouseenter",
            "button.pointermove",
            "button.mousemove",
            // Click
            "button.pointerdown",
            "button.mousedown",
            "button.focus",
            "button.focusin",
            "button.pointerup",
            "button.mouseup",
            "button.click",
        ]);
    });

    test("dblclick", async () => {
        await mountOnFixture(/* xml */ `<button autofocus="" type="button">Click me</button>`);
        monitorEvents("button");

        dblclick("button");

        expect.verifySteps([
            // Hover
            "button.pointerover",
            "button.mouseover",
            "button.pointerenter",
            "button.mouseenter",
            "button.pointermove",
            "button.mousemove",
            // Click 1
            "button.pointerdown",
            "button.mousedown",
            "button.focus",
            "button.focusin",
            "button.pointerup",
            "button.mouseup",
            "button.click",
            // Click 2
            "button.pointerdown",
            "button.mousedown",
            "button.pointerup",
            "button.mouseup",
            "button.click",
            // Double click event
            "button.dblclick",
        ]);
    });

    test("triple click", async () => {
        await mountOnFixture(/* xml */ `<button autofocus="" type="button">Click me</button>`);

        const allEvents = [
            // trigger 3 clicks
            click("button"),
            click("button"),
            click("button"),
        ].flat();

        const clickEvents = allEvents.filter((ev) => ev.type === "click");

        expect(clickEvents).toHaveLength(3);
        expect(allEvents.filter((ev) => ev.type === "dblclick")).toHaveLength(1);
        expect(clickEvents[0].detail).toBe(1);
        expect(clickEvents[1].detail).toBe(2);
        expect(clickEvents[2].detail).toBe(3);

        await advanceTime(1_000);

        const clickEvent = click("button").find((ev) => ev.type === "click");

        expect(clickEvent.detail).toBe(1);
    });

    test("click on common parent", async () => {
        await mountOnFixture(/* xml */ `
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

        pointerDown(".first");
        pointerUp(".second");

        expect.verifySteps([
            // Move to first
            "button.pointerover",
            "main.pointerover",
            "button.mouseover",
            "main.mouseover",
            "main.pointerenter",
            "button.pointerenter",
            "main.mouseenter",
            "button.mouseenter",
            "button.pointermove",
            "main.pointermove",
            "button.mousemove",
            "main.mousemove",
            // Pointer down on first
            "button.pointerdown",
            "main.pointerdown",
            "button.mousedown",
            "main.mousedown",
            "button.focus",
            "button.focusin",
            "main.focusin",
            // Move to second
            "button.pointermove",
            "main.pointermove",
            "button.mousemove",
            "main.mousemove",
            "button.pointerout",
            "main.pointerout",
            "button.mouseout",
            "main.mouseout",
            "button.pointerleave",
            "button.mouseleave",
            "input.pointerover",
            "main.pointerover",
            "input.mouseover",
            "main.mouseover",
            "input.pointerenter",
            "input.mouseenter",
            "input.pointermove",
            "main.pointermove",
            "input.mousemove",
            "main.mousemove",
            // Pointer up on second
            "input.pointerup",
            "main.pointerup",
            "input.mouseup",
            "main.mouseup",
            "main.click",
        ]);
    });

    test("click can be dispatched with pointer events prevented", async () => {
        await mountOnFixture(/* xml */ `<button type="button">Click me</button>`);

        const prevent = (ev) => ev.preventDefault();

        on("button", "pointerdown", prevent);
        on("button", "mousedown", prevent);
        on("button", "pointerup", prevent);
        on("button", "mouseup", prevent);

        hover("button");
        monitorEvents("button");

        click("button");

        expect.verifySteps(["button.pointerdown", "button.pointerup", "button.click"]);
    });

    test("click: iframe", async () => {
        await mountOnFixture(/* xml */ `
            <button>Click me</button>
            <iframe srcdoc="&lt;button&gt;iframe button&lt;/button&gt;" />
        `);

        await waitForIframes();

        expect("button").toHaveCount(1);
        expect(":iframe button").toHaveCount(1);

        click("button");

        expect("button").toBeFocused();
        expect(":iframe button").not.toBeFocused();

        click(":iframe button");

        expect("button").not.toBeFocused();
        expect(":iframe button").toBeFocused();
    });

    test("drag & drop: draggable items", async () => {
        await mountOnFixture(/* xml */ `
            <ul>
                <li id="first-item" draggable="true">Item 1</li>
                <li id="second-item" draggable="true">Item 2</li>
                <li id="third-item" draggable="true">Item 3</li>
            </ul>
        `);

        monitorEvents("body", (ev) => ev.type.startsWith("key") && formatKeyBoardEvent(ev));
        monitorEvents("li", (ev) => `${ev.target.id}.${ev.type}`);

        // Drag & cancel
        drag("#first-item").cancel();

        expect.verifySteps([
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            "first-item.focus",
            "first-item.focusin",
            // Cancel
            "keydown:Escape",
            "keyup:Escape",
        ]);

        // Drag & drop
        drag("#first-item").drop("#third-item");

        expect.verifySteps([
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            "first-item.focus",
            "first-item.focusin",
            // Leave first
            "first-item.dragstart",
            "first-item.drag",
            "first-item.dragover",
            "first-item.dragleave",
            // Move to third
            "third-item.dragenter",
            "third-item.drag",
            "third-item.dragover",
            // Drop
            "third-item.dragend",
        ]);

        // Drag, move & cancel
        drag("#first-item").moveTo("#third-item").cancel();

        expect.verifySteps([
            // Leave third
            "third-item.pointermove",
            "third-item.mousemove",
            "third-item.pointerout",
            "third-item.mouseout",
            "third-item.pointerleave",
            "third-item.mouseleave",
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            "first-item.focus",
            "first-item.focusin",
            // Leave first
            "first-item.dragstart",
            "first-item.drag",
            "first-item.dragover",
            "first-item.dragleave",
            // Move to third
            "third-item.dragenter",
            "third-item.drag",
            "third-item.dragover",
            // Cancel
            "keydown:Escape",
            "keyup:Escape",
        ]);

        // Drag, move & drop
        drag("#first-item").moveTo("#third-item").drop();

        expect.verifySteps([
            // Leave third
            "third-item.pointermove",
            "third-item.mousemove",
            "third-item.pointerout",
            "third-item.mouseout",
            "third-item.pointerleave",
            "third-item.mouseleave",
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            "first-item.focus",
            "first-item.focusin",
            // Leave first
            "first-item.dragstart",
            "first-item.drag",
            "first-item.dragover",
            "first-item.dragleave",
            // Move to third
            "third-item.dragenter",
            "third-item.drag",
            "third-item.dragover",
            // Drop
            "third-item.dragend",
        ]);

        // Drag, move & drop (different target)
        drag("#first-item").moveTo("#second-item").drop("#third-item");

        expect.verifySteps([
            // Leave third
            "third-item.pointermove",
            "third-item.mousemove",
            "third-item.pointerout",
            "third-item.mouseout",
            "third-item.pointerleave",
            "third-item.mouseleave",
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            "first-item.focus",
            "first-item.focusin",
            // Leave first
            "first-item.dragstart",
            "first-item.drag",
            "first-item.dragover",
            "first-item.dragleave",
            // Move to second
            "second-item.dragenter",
            "second-item.drag",
            "second-item.dragover",
            // Leave second
            "second-item.drag",
            "second-item.dragover",
            "second-item.dragleave",
            // Move to third
            "third-item.dragenter",
            "third-item.drag",
            "third-item.dragover",
            // Drop
            "third-item.dragend",
        ]);
    });

    test("drag & drop: non-draggable items", async () => {
        await mountOnFixture(/* xml */ `
            <ul>
                <li id="first-item">Item 1</li>
                <li id="second-item">Item 2</li>
                <li id="third-item">Item 3</li>
            </ul>
        `);

        monitorEvents("body", (ev) => ev.type.startsWith("key") && formatKeyBoardEvent(ev));
        monitorEvents("li", (ev) => `${ev.target.id}.${ev.type}`);

        // Drag & cancel
        drag("#first-item").cancel();

        expect.verifySteps([
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            // Cancel
            "keydown:Escape",
            "keyup:Escape",
        ]);

        // Drag & drop
        drag("#first-item").drop("#third-item");

        expect.verifySteps([
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            // Leave first
            "first-item.pointermove",
            "first-item.mousemove",
            "first-item.pointerout",
            "first-item.mouseout",
            "first-item.pointerleave",
            "first-item.mouseleave",
            // Move to third
            "third-item.pointerover",
            "third-item.mouseover",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.pointermove",
            "third-item.mousemove",
            // Drop
            "third-item.pointerup",
            "third-item.mouseup",
        ]);

        // Drag, move & cancel
        drag("#first-item").moveTo("#third-item").cancel();

        expect.verifySteps([
            // Leave third
            "third-item.pointermove",
            "third-item.mousemove",
            "third-item.pointerout",
            "third-item.mouseout",
            "third-item.pointerleave",
            "third-item.mouseleave",
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            // Leave first
            "first-item.pointermove",
            "first-item.mousemove",
            "first-item.pointerout",
            "first-item.mouseout",
            "first-item.pointerleave",
            "first-item.mouseleave",
            // Move to third
            "third-item.pointerover",
            "third-item.mouseover",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.pointermove",
            "third-item.mousemove",
            // Cancel
            "keydown:Escape",
            "keyup:Escape",
        ]);

        // Drag, move & drop
        drag("#first-item").moveTo("#third-item").drop();

        expect.verifySteps([
            // Leave third
            "third-item.pointermove",
            "third-item.mousemove",
            "third-item.pointerout",
            "third-item.mouseout",
            "third-item.pointerleave",
            "third-item.mouseleave",
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            // Leave first
            "first-item.pointermove",
            "first-item.mousemove",
            "first-item.pointerout",
            "first-item.mouseout",
            "first-item.pointerleave",
            "first-item.mouseleave",
            // Move to third
            "third-item.pointerover",
            "third-item.mouseover",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.pointermove",
            "third-item.mousemove",
            // Drop
            "third-item.pointerup",
            "third-item.mouseup",
        ]);

        // Drag, move & drop (different target)
        drag("#first-item").moveTo("#second-item").drop("#third-item");

        expect.verifySteps([
            // Leave third
            "third-item.pointermove",
            "third-item.mousemove",
            "third-item.pointerout",
            "third-item.mouseout",
            "third-item.pointerleave",
            "third-item.mouseleave",
            // Move to first
            "first-item.pointerover",
            "first-item.mouseover",
            "first-item.pointerenter",
            "first-item.mouseenter",
            "first-item.pointermove",
            "first-item.mousemove",
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
            // Leave first
            "first-item.pointermove",
            "first-item.mousemove",
            "first-item.pointerout",
            "first-item.mouseout",
            "first-item.pointerleave",
            "first-item.mouseleave",
            // Move to second
            "second-item.pointerover",
            "second-item.mouseover",
            "second-item.pointerenter",
            "second-item.mouseenter",
            "second-item.pointermove",
            "second-item.mousemove",
            // Leave second
            "second-item.pointermove",
            "second-item.mousemove",
            "second-item.pointerout",
            "second-item.mouseout",
            "second-item.pointerleave",
            "second-item.mouseleave",
            // Move to third
            "third-item.pointerover",
            "third-item.mouseover",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.pointermove",
            "third-item.mousemove",
            // Drop
            "third-item.pointerup",
            "third-item.mouseup",
        ]);
    });

    test("fill: text", async () => {
        await mountOnFixture(/* xml */ `<input type="text" value="" />`);

        expect("input").not.toHaveValue();
        expect.verifySteps([]);

        click("input");

        monitorEvents("input");

        fill("Test value");

        expect("input").toHaveValue("Test value");
        expect.verifySteps([
            ...[..."Test value"].flatMap(() => [
                "input.keydown",
                "input.beforeinput",
                "input.input",
                "input.keyup",
            ]),
        ]);
    });

    test("fill: text with previous value", async () => {
        await mountOnFixture(/* xml */ `<input type="text" value="Test" />`);

        expect("input").toHaveValue("Test");

        click("input");
        fill(" value");

        expect("input").toHaveValue("Test value");
    });

    test("fill: number", async () => {
        await mountOnFixture(/* xml */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        click("input");
        fill(42);

        expect("input").toHaveValue(42);
    });

    test("fill: email", async () => {
        await mountOnFixture(/* xml */ `<input type="email" />`);

        expect("input").not.toHaveValue();

        click("input");
        fill("john@doe.com");

        expect("input").toHaveValue("john@doe.com");
    });

    test("edit on empty value", async () => {
        await mountOnFixture(/* xml */ `<input type="text" />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        expect("input").not.toHaveValue();

        edit("test value");

        expect("input").toHaveValue("test value");
        expect.verifySteps([
            ...[..."test value"].flatMap((char) => [
                `keydown:${char}`,
                `beforeinput`,
                `input`,
                `keyup:${char}`,
            ]),
        ]);

        click(getFixture());

        expect.verifySteps([
            // Pointer out
            "pointermove",
            "mousemove",
            "pointerout",
            "mouseout",
            "pointerleave",
            "mouseleave",
            // Change
            "blur",
            "focusout",
            "change",
        ]);
    });

    test("edit on existing value", async () => {
        await mountOnFixture(/* xml */ `<input type="text" value="Test" />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        expect("input").toHaveValue("Test");

        edit(" value");

        expect("input").toHaveValue(" value");
        expect.verifySteps([
            // Clear
            "keydown:a.ctrl",
            "select",
            "keyup:a.ctrl",
            "keydown:Backspace",
            "beforeinput",
            "input",
            "keyup:Backspace",
            // Fill
            ...[..." value"].flatMap((char) => [
                `keydown:${char}`,
                `beforeinput`,
                `input`,
                `keyup:${char}`,
            ]),
        ]);
    });

    test("edit: iframe", async () => {
        await mountOnFixture(/* xml */ `
            <input type="text" />
            <iframe srcdoc="&lt;input type='text' /&gt;" />
        `);

        await waitForIframes();

        expect("input").toHaveCount(1);
        expect(":iframe input").toHaveCount(1);

        on("input", "change", () => expect.step("top:change"));
        on(":iframe input", "change", () => expect.step("iframe:change"));

        click("input");
        edit("abc");

        expect.verifySteps([]);
        expect("input").toHaveValue("abc");
        expect(":iframe input").toHaveValue("");

        click(":iframe input");
        edit("def");

        expect.verifySteps(["top:change"]);
        expect("input").toHaveValue("abc");
        expect(":iframe input").toHaveValue("def");

        click(":iframe body");
        expect.verifySteps(["iframe:change"]);
    });

    test("setInputFiles: single file", async () => {
        await mountOnFixture(/* xml */ `<input type="file" />`);
        const file1 = new File([""], "file1.txt");
        const file2 = new File([""], "file2.txt");

        expect("input").not.toHaveValue();

        click("input");
        setInputFiles(file1);

        expect("input").toHaveValue(/file1\.txt/);
        expect("input").toHaveValue([file1]);

        click("input");
        setInputFiles(file2);

        expect("input").toHaveValue(/file2\.txt/);
        expect("input").toHaveValue([file2]);
    });

    test("setInputFiles: multiple files", async () => {
        await mountOnFixture(/* xml */ `<input type="file" multiple="multiple" />`);
        const file1 = new File([""], "file1.txt");
        const file2 = new File([""], "file2.txt");

        expect("input").not.toHaveValue();

        click("input");
        setInputFiles(file1);

        expect("input").toHaveValue(/file1\.txt/);
        expect("input").toHaveValue([file1]);

        click("input");
        setInputFiles([file1, file2]);

        expect("input").toHaveValue([file1, file2]);
    });

    test("setInputFiles: hidden input with label", async () => {
        await mountOnFixture(/* xml */ `
            <label for="file-input">Label</label>
            <input id="file-input" style="display: none" type="file" />
        `);

        expect("input").not.toBeVisible();
        expect("input").not.toHaveValue();
        expect("label").toBeVisible();

        click("label");
        setInputFiles(new File([""], "file.txt"));

        expect("input").toHaveValue(/file\.txt/);
    });

    test("setInputFiles: hidden input with programmatic click", async () => {
        await mountOnFixture(/* xml */ `
            <button>upload</button>
            <input style="display: none" type="file" />
        `);

        on("button", "click", () => queryOne("input").click());

        expect("input").not.toBeVisible();
        expect("input").not.toHaveValue();
        expect("button").toBeVisible();

        click("button");
        setInputFiles(new File([""], "file.txt"));

        expect("input").toHaveValue(/file\.txt/);
    });

    test("setInputRange: basic case and events", async () => {
        await mountOnFixture(/* xml */ `<input type="range" min="10" max="40" />`);

        monitorEvents("input");

        setInputRange("input", 30);

        expect("input").toHaveValue(30);
        expect.verifySteps([
            // Hover input
            "input.pointerover",
            "input.mouseover",
            "input.pointerenter",
            "input.mouseenter",
            "input.pointermove",
            "input.mousemove",
            // Pointer down
            "input.pointerdown",
            "input.mousedown",
            "input.focus",
            "input.focusin",
            // Set range
            "input.input",
            "input.change",
            // Pointer up
            "input.pointerup",
            "input.mouseup",
            "input.click",
        ]);
    });

    test("setInputRange: out of min and max values", async () => {
        await mountOnFixture(/* xml */ `<input type="range" min="10" max="40" />`);

        setInputRange("input", 5);

        expect("input").toHaveValue(10);

        setInputRange("input", 50);

        expect("input").toHaveValue(40);
    });

    test("hover", async () => {
        await mountOnFixture(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        hover("button");

        expect.verifySteps([
            "button.pointerover",
            "button.mouseover",
            "button.pointerenter",
            "button.mouseenter",
            "button.pointermove",
            "button.mousemove",
        ]);

        hover("button");

        expect.verifySteps(["button.pointermove", "button.mousemove"]);
    });

    test("leave", async () => {
        await mountOnFixture(/* xml */ `<button type="button">Click me</button>`);

        hover("button");

        monitorEvents("button");

        leave();

        expect.verifySteps([
            "button.pointermove",
            "button.mousemove",
            "button.pointerout",
            "button.mouseout",
            "button.pointerleave",
            "button.mouseleave",
        ]);
    });

    test("keyDown", async () => {
        await mountOnFixture(/* xml */ `<input type="text" />`);

        click("input");

        monitorEvents("input");

        keyDown("a");

        expect.verifySteps(["input.keydown", "input.beforeinput", "input.input"]);

        keyUp("a");

        expect("input").toHaveValue("a");
        expect.verifySteps(["input.keyup"]);
    });

    test("multiple keyDown should be flagged as repeated", async () => {
        const getKeyDownEvent = () => events.find((ev) => ev.type === "keydown");
        let events;

        await mountOnFixture(/* xml */ `<input type="text" />`);

        click("input");

        monitorEvents("input");

        events = keyDown("Enter");
        expect(getKeyDownEvent().repeat).toBe(false);

        events = keyDown("Enter");
        expect(getKeyDownEvent().repeat).toBe(true);

        events = keyDown("Enter");
        expect(getKeyDownEvent().repeat).toBe(true);

        events = keyDown("Escape");
        expect(getKeyDownEvent().repeat).toBe(false);

        events = keyDown("Enter");
        expect(getKeyDownEvent().repeat).toBe(false);

        events = keyUp("Enter");
        expect(getKeyDownEvent()).toBe(undefined);

        events = keyDown("Enter");
        expect(getKeyDownEvent().repeat).toBe(false);

        events = keyDown("Enter");
        expect(getKeyDownEvent().repeat).toBe(true);

        expect.verifySteps([
            "input.keydown",
            "input.keydown",
            "input.keydown",
            "input.keydown",
            "input.keydown",
            "input.keyup",
            "input.keydown",
            "input.keydown",
        ]);
    });

    test("pointerDown", async () => {
        await mountOnFixture(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        pointerDown("button");

        expect.verifySteps([
            // Pointer enter on button
            "button.pointerover",
            "button.mouseover",
            "button.pointerenter",
            "button.mouseenter",
            "button.pointermove",
            "button.mousemove",
            // Pointer down
            "button.pointerdown",
            "button.mousedown",
            "button.focus",
            "button.focusin",
        ]);

        pointerUp("button");

        expect.verifySteps(["button.pointerup", "button.mouseup", "button.click"]);
    });

    test("press key on text input", async () => {
        await mountOnFixture(/* xml */ `<input type="text" />`);

        click("input");

        monitorEvents("input");

        press("a");

        expect("input").toHaveValue("a");
        expect.verifySteps(["input.keydown", "input.beforeinput", "input.input", "input.keyup"]);
    });

    test("press key on number input", async () => {
        await mountOnFixture(/* xml */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        click("input");
        press("4");

        expect("input").toHaveValue(4);

        press("2");

        expect("input").toHaveValue(42);
    });

    test("press arrow keys on input", async () => {
        await mountOnFixture(/* xml */ `<input value="value" />`);

        click("input");

        expect("input").toHaveProperty("selectionStart", 5);
        expect("input").toHaveProperty("selectionEnd", 5);

        press("left");

        expect("input").toHaveProperty("selectionStart", 4);
        expect("input").toHaveProperty("selectionEnd", 4);

        press("left");
        press("left");
        press("right");

        expect("input").toHaveProperty("selectionStart", 3);
        expect("input").toHaveProperty("selectionEnd", 3);

        press(["control", "a"]);

        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 5);

        press("right");

        expect("input").toHaveProperty("selectionStart", 5);
        expect("input").toHaveProperty("selectionEnd", 5);

        press(["ctrl", "a"]);
        press("down");

        expect("input").toHaveProperty("selectionStart", 5);
        expect("input").toHaveProperty("selectionEnd", 5);

        press(["ctrl", "a"]);
        press("left");

        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 0);

        press(["ctrl", "a"]);
        press("up");

        expect("input").toHaveProperty("selectionStart", 0);
        expect("input").toHaveProperty("selectionEnd", 0);
    });

    test("insert character updates selection", async () => {
        await mountOnFixture(/* xml */ `<input value="abc" />`);

        click("input");

        const input = queryOne("input");
        input.selectionStart = 0;
        input.selectionEnd = 3;

        press("d");

        expect("input").toHaveValue("d");
        expect("input").toHaveProperty("selectionStart", 1);
        expect("input").toHaveProperty("selectionEnd", 1);

        press("f");

        expect("input").toHaveValue("df");
        expect("input").toHaveProperty("selectionStart", 2);
        expect("input").toHaveProperty("selectionEnd", 2);

        input.selectionStart = 1;
        input.selectionEnd = 1;

        press("e");

        expect("input").toHaveValue("def");
        expect("input").toHaveProperty("selectionStart", 2);
        expect("input").toHaveProperty("selectionEnd", 2);
    });

    test("press 'Enter' on form input", async () => {
        await mountOnFixture(/* xml */ `
            <form t-on-submit.prevent="">
                <input type="text" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("input");

        expect("input").not.toBeFocused();

        press("Tab");

        expect("input").toBeFocused();

        press("Enter");

        expect.verifySteps([
            // Tab
            "input.focus",
            "input.focusin",
            "form.focusin",
            // Enter
            "input.keydown",
            "form.keydown",
            "form.submit",
            "input.keyup",
            "form.keyup",
        ]);
    });

    test("press 'Enter' on form button", async () => {
        await mountOnFixture(/* xml */ `
            <form t-on-submit.prevent="">
                <button type="button" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("button");

        expect("button").not.toBeFocused();

        press("Tab");

        expect("button").toBeFocused();

        press("Enter");

        expect.verifySteps([
            // Tab
            "button.focus",
            "button.focusin",
            "form.focusin",
            // Enter
            "button.keydown",
            "form.keydown",
            "button.click",
            "form.click",
            "button.keyup",
            "form.keyup",
        ]);
    });

    test("press 'Enter' on form submit button", async () => {
        await mountOnFixture(/* xml */ `
            <form t-on-submit.prevent="">
                <button type="submit" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("button");

        expect("button").not.toBeFocused();

        press("Tab");

        expect("button").toBeFocused();

        press("Enter");

        expect.verifySteps([
            // Tab
            "button.focus",
            "button.focusin",
            "form.focusin",
            // Enter
            "button.keydown",
            "form.keydown",
            "form.submit",
            "button.keyup",
            "form.keyup",
        ]);
    });

    test("press 'Space' on checkbox input", async () => {
        await mountOnFixture(/* xml */ `<input type="checkbox" checked="" />`);

        expect("input").toHaveProperty("checked", true);

        uncheck("input"); // true -> false

        expect("input").toHaveProperty("checked", false);

        monitorEvents("input");

        press(" "); // false -> true

        expect("input").toHaveProperty("checked", true);
        expect.verifySteps([
            // Key press
            "input.keydown",
            "input.beforeinput",
            "input.input",
            "input.keyup",
            // Click triggered by key press
            "input.click",
            "input.input",
            "input.change",
        ]);
    });

    test("press 'Backspace' on number input", async () => {
        await mountOnFixture(/* xml */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        click("input");
        press("Backspace");

        expect("input").toHaveValue(42);

        press("Backspace");

        expect("input").toHaveValue(4);
    });

    test("press 'Enter' on textarea", async () => {
        await mountOnFixture(/* xml */ `<textarea t-att-value="'aaa'" />`);

        expect("textarea").toHaveValue("aaa");

        click("textarea");
        press("Enter");

        expect("textarea").toHaveValue("aaa\n");
    });

    test("special keys modifiers: Windows", async () => {
        mockUserAgent("windows");

        await mountOnFixture(/* xml */ `<input />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        press("alt");

        expect.verifySteps(["keydown:Alt.alt", "keyup:Alt.alt"]);

        press("ctrl");

        expect.verifySteps(["keydown:Control.ctrl", "keyup:Control.ctrl"]);

        press("meta");

        expect.verifySteps(["keydown:Meta.meta", "keyup:Meta.meta"]);

        press("shift");

        expect.verifySteps(["keydown:Shift.shift", "keyup:Shift.shift"]);
    });

    test("special keys modifiers: Mac", async () => {
        mockUserAgent("mac");

        await mountOnFixture(/* xml */ `<input />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        press("alt");

        expect.verifySteps(["keydown:Alt.alt", "keyup:Alt.alt"]);

        press("ctrl");

        expect.verifySteps(["keydown:Control.ctrl", "keyup:Control.ctrl"]);

        press("meta");

        expect.verifySteps(["keydown:Meta.meta", "keyup:Meta.meta"]);

        press("shift");

        expect.verifySteps(["keydown:Shift.shift", "keyup:Shift.shift"]);
    });

    test("compose shift, alt and control and a key", async () => {
        await mountOnFixture(/* xml */ `<input />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        press(["ctrl", "b"]);

        expect.verifySteps([
            "keydown:Control.ctrl",
            "keydown:b.ctrl",
            "keyup:b.ctrl",
            "keyup:Control.ctrl",
        ]);

        press(["shift", "b"]);

        expect.verifySteps([
            "keydown:Shift.shift",
            "keydown:b.shift",
            "beforeinput",
            "input",
            "keyup:b.shift",
            "keyup:Shift.shift",
        ]);

        press(["Alt", "Control", "b"]);

        expect.verifySteps([
            "keydown:Alt.alt",
            "keydown:Control.alt.ctrl",
            "keydown:b.alt.ctrl",
            "keyup:b.alt.ctrl",
            "keyup:Control.alt.ctrl",
            "keyup:Alt.alt",
        ]);
    });

    test("scroll", async () => {
        await mountOnFixture(/* xml */ `
            <div class="scrollable" style="height: 200px; width: 200px; overflow: auto;">
                <div style="height: 2000px; width: 2000px;"></div>
            </div>
        `);

        monitorEvents(".scrollable");

        scroll(".scrollable", { top: 500 });
        await animationFrame();

        expect(".scrollable").toHaveProperty("scrollTop", 500);
        expect(".scrollable").toHaveProperty("scrollLeft", 0);
        expect.verifySteps(["div.wheel", "div.scroll", "div.scrollend"]);

        scroll(".scrollable", { left: 1200 });
        await animationFrame();

        expect(".scrollable").toHaveProperty("scrollTop", 500);
        expect(".scrollable").toHaveProperty("scrollLeft", 1200);
        expect.verifySteps(["div.wheel", "div.scroll", "div.scrollend"]);
    });

    test("resize", async () => {
        await mountOnFixture(/* xml */ `
            <div class="resizable" style="height: 200px; width: 200px; overflow: auto;"/>
        `);

        const { innerHeight } = window;

        window.addEventListener("resize", () => expect.step("window.resize"));

        resize({ width: 300 });

        expect(window.innerWidth).toBe(300);
        expect(window.innerHeight).toBe(innerHeight);

        expect.verifySteps(["window.resize"]);

        resize({ height: 264 });

        expect(window.innerWidth).toBe(300);
        expect(window.innerHeight).toBe(264);

        expect.verifySteps(["window.resize"]);
    });

    test("select", async () => {
        await mountOnFixture(/* xml */ `
            <select>
                <option value="a">A</option>
                <option value="b">B</option>
                <option value="c">C</option>
            </select>
        `);

        expect("select").toHaveValue("a"); // default to first option
        expect.verifySteps([]);

        click("select");

        monitorEvents("select");

        select("b");

        expect("select").toHaveValue("b");
        expect.verifySteps(["select.change"]);
    });

    test("can trigger synthetic event handlers", async () => {
        await mountOnFixture(
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

        click("button");

        expect.verifySteps(["click"]);
    });

    test("synthetic event handlers are not cleaned up between tests", async () => {
        await mountOnFixture(
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

        click("button");

        expect.verifySteps(["clack"]);
    });
});
