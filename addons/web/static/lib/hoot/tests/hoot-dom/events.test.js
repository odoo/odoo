/** @odoo-module */

import { Component, xml } from "@odoo/owl";
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
} from "../../../hoot-dom/hoot-dom";
import { after, describe, expect, mountOnFixture, test } from "../../hoot";
import { mockUserAgent } from "../../mock/navigator";
import { animationFrame } from "../../mock/time";
import { parseUrl } from "../local_helpers";

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
    formatStep ||= (ev) => `${ev.currentTarget.tagName.toLowerCase()}.${ev.type}`;

    for (const element of document.querySelectorAll(target)) {
        for (const prop in element) {
            const type = prop.match(/^on(\w+)/)?.[1];
            if (!type) {
                continue;
            }
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
        }
    }
};

describe(parseUrl(import.meta.url), () => {
    test("clear", async () => {
        await mountOnFixture(/* xml */ `<input type="text" value="Test" />`);

        expect("input").toHaveValue("Test");
        expect([]).toVerifySteps();

        click("input");

        monitorEvents("input");

        clear();

        expect("input").not.toHaveValue();
        expect([
            "input.keydown",
            "input.select",
            "input.keyup",
            "input.keydown",
            "input.beforeinput",
            "input.input",
            "input.keyup",
        ]).toVerifySteps();
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

        expect([
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
            "button.pointerup",
            "button.mouseup",
            "button.click",
        ]).toVerifySteps();
    });

    test("dblclick", async () => {
        await mountOnFixture(/* xml */ `<button autofocus="" type="button">Click me</button>`);
        monitorEvents("button");

        dblclick("button");

        expect([
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
        ]).toVerifySteps();
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

        expect([
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
        ]).toVerifySteps();

        // Drag & drop
        drag("#first-item").drop("#third-item");

        expect([
            // Drag first
            "first-item.pointerdown",
            "first-item.mousedown",
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
        ]).toVerifySteps();

        // Drag, move & cancel
        drag("#first-item").moveTo("#third-item").cancel();

        expect([
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
        ]).toVerifySteps();

        // Drag, move & drop
        drag("#first-item").moveTo("#third-item").drop();

        expect([
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
        ]).toVerifySteps();

        // Drag, move & drop (different target)
        drag("#first-item").moveTo("#second-item").drop("#third-item");

        expect([
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
        ]).toVerifySteps();
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

        expect([
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
        ]).toVerifySteps();

        // Drag & drop
        drag("#first-item").drop("#third-item");

        expect([
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
        ]).toVerifySteps();

        // Drag, move & cancel
        drag("#first-item").moveTo("#third-item").cancel();

        expect([
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
        ]).toVerifySteps();

        // Drag, move & drop
        drag("#first-item").moveTo("#third-item").drop();

        expect([
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
        ]).toVerifySteps();

        // Drag, move & drop (different target)
        drag("#first-item").moveTo("#second-item").drop("#third-item");

        expect([
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
        ]).toVerifySteps();
    });

    test("fill: text", async () => {
        await mountOnFixture(/* xml */ `<input type="text" value="" />`);

        expect("input").not.toHaveValue();
        expect([]).toVerifySteps();

        click("input");

        monitorEvents("input");

        fill("Test value");

        expect("input").toHaveValue("Test value");
        expect([
            ...[..."Test value"].flatMap(() => [
                "input.keydown",
                "input.beforeinput",
                "input.input",
                "input.keyup",
            ]),
        ]).toVerifySteps();
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
        expect([
            ...[..."test value"].flatMap((char) => [
                `keydown:${char}`,
                `beforeinput`,
                `input`,
                `keyup:${char}`,
            ]),
        ]).toVerifySteps();
    });

    test("edit on existing value", async () => {
        await mountOnFixture(/* xml */ `<input type="text" value="Test" />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        expect("input").toHaveValue("Test");

        edit(" value");

        expect("input").toHaveValue(" value");
        expect([
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
        ]).toVerifySteps();
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
        expect([
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
            // Set range
            "input.input",
            "input.change",
            // Pointer up
            "input.pointerup",
            "input.mouseup",
            "input.click",
        ]).toVerifySteps();
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

        expect([
            "button.pointerover",
            "button.mouseover",
            "button.pointerenter",
            "button.mouseenter",
            "button.pointermove",
            "button.mousemove",
        ]).toVerifySteps();

        hover("button");

        expect(["button.pointermove", "button.mousemove"]).toVerifySteps();
    });

    test("leave", async () => {
        await mountOnFixture(/* xml */ `<button type="button">Click me</button>`);

        hover("button");

        monitorEvents("button");

        leave();

        expect([
            "button.pointermove",
            "button.mousemove",
            "button.pointerout",
            "button.mouseout",
            "button.pointerleave",
            "button.mouseleave",
        ]).toVerifySteps();
    });

    test("keyDown", async () => {
        await mountOnFixture(/* xml */ `<input type="text" />`);

        click("input");

        monitorEvents("input");

        keyDown("a");

        expect(["input.keydown", "input.beforeinput", "input.input"]).toVerifySteps();

        keyUp("a");

        expect("input").toHaveValue("a");
        expect(["input.keyup"]).toVerifySteps();
    });

    test("pointerDown", async () => {
        await mountOnFixture(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        pointerDown("button");

        expect([
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
        ]).toVerifySteps();

        pointerUp("button");

        expect(["button.pointerup", "button.mouseup", "button.click"]).toVerifySteps();
    });

    test("press key on text input", async () => {
        await mountOnFixture(/* xml */ `<input type="text" />`);

        click("input");

        monitorEvents("input");

        press("a");

        expect("input").toHaveValue("a");
        expect([
            "input.keydown",
            "input.beforeinput",
            "input.input",
            "input.keyup",
        ]).toVerifySteps();
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

        expect([
            // Tab
            "input.focus",
            // Enter
            "input.keydown",
            "form.keydown",
            "input.keyup",
            "form.keyup",
            // Form submit
            "form.submit",
        ]).toVerifySteps();
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

        expect([
            // Tab
            "button.focus",
            // Enter
            "button.keydown",
            "form.keydown",
            "button.keyup",
            "form.keyup",
            // Click triggered by Enter
            "button.click",
            "form.click",
        ]).toVerifySteps();
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

        expect([
            // Tab
            "button.focus",
            // Enter
            "button.keydown",
            "form.keydown",
            "button.keyup",
            "form.keyup",
            // Form submit
            "form.submit",
        ]).toVerifySteps();
    });

    test("press 'Space' on checkbox input", async () => {
        await mountOnFixture(/* xml */ `<input type="checkbox" checked="" />`);

        expect("input").toHaveProperty("checked", true);

        uncheck("input"); // true -> false

        expect("input").toHaveProperty("checked", false);

        monitorEvents("input");

        press(" "); // false -> true

        expect("input").toHaveProperty("checked", true);
        expect([
            // Key press
            "input.keydown",
            "input.beforeinput",
            "input.input",
            "input.keyup",
            // Click triggered by key press
            "input.click",
            "input.input",
            "input.change",
        ]).toVerifySteps();
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

        expect(["keydown:Alt.alt", "keyup:Alt.alt"]).toVerifySteps();

        press("ctrl");

        expect(["keydown:Control.ctrl", "keyup:Control.ctrl"]).toVerifySteps();

        press("meta");

        expect(["keydown:Meta.meta", "keyup:Meta.meta"]).toVerifySteps();

        press("shift");

        expect(["keydown:Shift.shift", "keyup:Shift.shift"]).toVerifySteps();
    });

    test("special keys modifiers: Mac", async () => {
        mockUserAgent("mac");

        await mountOnFixture(/* xml */ `<input />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        press("alt");

        expect(["keydown:Alt.alt", "keyup:Alt.alt"]).toVerifySteps();

        press("ctrl");

        expect(["keydown:Control.ctrl", "keyup:Control.ctrl"]).toVerifySteps();

        press("meta");

        expect(["keydown:Meta.meta", "keyup:Meta.meta"]).toVerifySteps();

        press("shift");

        expect(["keydown:Shift.shift", "keyup:Shift.shift"]).toVerifySteps();
    });

    test("compose shift, alt and control and a key", async () => {
        await mountOnFixture(/* xml */ `<input />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        press(["ctrl", "b"]);

        expect([
            "keydown:Control.ctrl",
            "keydown:b.ctrl",
            "keyup:b.ctrl",
            "keyup:Control.ctrl",
        ]).toVerifySteps();

        press("shift+b");

        expect([
            "keydown:Shift.shift",
            "keydown:b.shift",
            "beforeinput",
            "input",
            "keyup:b.shift",
            "keyup:Shift.shift",
        ]).toVerifySteps();

        press("Alt+Control+b");

        expect([
            "keydown:Alt.alt",
            "keydown:Control.alt.ctrl",
            "keydown:b.alt.ctrl",
            "keyup:b.alt.ctrl",
            "keyup:Control.alt.ctrl",
            "keyup:Alt.alt",
        ]).toVerifySteps();
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
        expect(["div.wheel", "div.scroll", "div.scrollend"]).toVerifySteps();

        scroll(".scrollable", { left: 1200 });
        await animationFrame();

        expect(".scrollable").toHaveProperty("scrollTop", 500);
        expect(".scrollable").toHaveProperty("scrollLeft", 1200);
        expect(["div.wheel", "div.scroll", "div.scrollend"]).toVerifySteps();
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

        expect(["window.resize"]).toVerifySteps();

        resize({ height: 264 });

        expect(window.innerWidth).toBe(300);
        expect(window.innerHeight).toBe(264);

        expect(["window.resize"]).toVerifySteps();
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
        expect([]).toVerifySteps();

        click("select");

        monitorEvents("select");

        select("b");

        expect("select").toHaveValue("b");
        expect(["select.change"]).toVerifySteps();
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

        expect(["click"]).toVerifySteps();
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

        expect(["clack"]).toVerifySteps();
    });
});
