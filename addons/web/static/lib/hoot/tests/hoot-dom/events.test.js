/** @odoo-module */

import {
    clear,
    click,
    drag,
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
    scroll,
    select,
    setInputFiles,
    uncheck,
} from "../../../hoot-dom/hoot-dom";
import { after, describe, expect, test } from "../../hoot";
import { mockUserAgent } from "../../mock/navigator";
import { mount, parseUrl } from "../local_helpers";

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
            const off = on(element, type, (ev) => {
                expect.step(formatStep(ev));
                if (ev.type === "submit") {
                    ev.preventDefault();
                }
            });
            after(off);
        }
    }
};

describe(parseUrl(import.meta.url), () => {
    test.tags`no focus`("clear", async () => {
        await mount(/* xml */ `<input type="text" value="Test" />`);
        monitorEvents("input");

        expect("input").toHaveValue("Test");
        expect([]).toVerifySteps();

        click("input");
        clear();

        expect("input").not.toHaveValue();
        expect([
            // Click
            "input.pointerdown",
            "input.mousedown",
            "input.focus",
            "input.pointerup",
            "input.mouseup",
            "input.click",
            // Clear
            "input.keydown",
            "input.select",
            "input.keyup",
            "input.keydown",
            "input.input",
            "input.keyup",
        ]).toVerifySteps();
    });

    test("clear: email", async () => {
        await mount(/* xml */ `<input type="email" value="john@doe.com" />`);

        expect("input").toHaveValue("john@doe.com");

        click("input");
        clear();

        expect("input").toHaveValue("");
    });

    test("clear: number", async () => {
        await mount(/* xml */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        click("input");
        clear();

        expect("input").not.toHaveValue();
    });

    test("clear: files", async () => {
        await mount(/* xml */ `<input type="file" />`);
        const file = new File([""], "file.txt");

        expect("input").not.toHaveValue();

        click("input");
        fill(file);

        expect("input").toHaveValue([file]);

        clear();

        expect("input").not.toHaveValue();
    });

    test.tags`no focus`("click", async () => {
        await mount(/* xml */ `<button autofocus="" type="button">Click me</button>`);
        monitorEvents("button");

        click("button");

        expect([
            "button.pointerdown",
            "button.mousedown",
            "button.focus",
            "button.pointerup",
            "button.mouseup",
            "button.click",
        ]).toVerifySteps();
    });

    test("drag & drop: draggable items", async () => {
        await mount(/* xml */ `
            <ul>
                <li id="first-item" draggable="true">Item 1</li>
                <li id="second-item" draggable="true">Item 2</li>
                <li id="third-item" draggable="true">Item 3</li>
            </ul>
        `);

        monitorEvents("body");
        monitorEvents("li", (ev) => `${ev.target.id}.${ev.type}`);

        // Drag & cancel
        drag("#first-item").cancel();

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",
            "first-item.dragstart",
            "body.dragstart",
            // Cancel
            "body.keydown",
            "body.keyup",
        ]).toVerifySteps();

        // Drag & drop
        drag("#first-item").drop("#third-item");

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",
            "first-item.dragstart",
            "body.dragstart",
            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "first-item.drag",
            "body.drag",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.dragenter",
            "body.dragenter",
            // Drop
            "third-item.pointerup",
            "body.pointerup",
            "third-item.mouseup",
            "body.mouseup",
            "third-item.dragend",
            "body.dragend",
        ]).toVerifySteps();

        // Drag, move & cancel
        drag("#first-item").moveTo("#third-item").cancel();

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",
            "first-item.dragstart",
            "body.dragstart",
            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "first-item.drag",
            "body.drag",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.dragenter",
            "body.dragenter",
            // Cancel
            "body.keydown",
            "body.keyup",
        ]).toVerifySteps();

        // Drag, move & drop
        drag("#first-item").moveTo("#third-item").drop();

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",
            "first-item.dragstart",
            "body.dragstart",
            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "first-item.drag",
            "body.drag",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.dragenter",
            "body.dragenter",
            // Drop
            "third-item.pointerup",
            "body.pointerup",
            "third-item.mouseup",
            "body.mouseup",
            "third-item.dragend",
            "body.dragend",
        ]).toVerifySteps();

        // Drag, move & drop (different target)
        drag("#first-item").moveTo("#second-item").drop("#third-item");

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",
            "first-item.dragstart",
            "body.dragstart",
            // Move to second
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "first-item.drag",
            "body.drag",
            "second-item.pointerenter",
            "second-item.mouseenter",
            "second-item.dragenter",
            "body.dragenter",
            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "first-item.drag",
            "body.drag",
            "third-item.pointerenter",
            "third-item.mouseenter",
            "third-item.dragenter",
            "body.dragenter",
            // Drop
            "third-item.pointerup",
            "body.pointerup",
            "third-item.mouseup",
            "body.mouseup",
            "third-item.dragend",
            "body.dragend",
        ]).toVerifySteps();
    });

    test("drag & drop: non-draggable items", async () => {
        await mount(/* xml */ `
            <ul>
                <li id="first-item">Item 1</li>
                <li id="second-item">Item 2</li>
                <li id="third-item">Item 3</li>
            </ul>
        `);

        monitorEvents("body");
        monitorEvents("li", (ev) => `${ev.target.id}.${ev.type}`);

        // Drag & cancel
        drag("#first-item").cancel();

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",

            // Cancel
            "body.keydown",
            "body.keyup",
        ]).toVerifySteps();

        // Drag & drop
        drag("#first-item").drop("#third-item");

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",

            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "third-item.pointerenter",
            "third-item.mouseenter",

            // Drop
            "third-item.pointerup",
            "body.pointerup",
            "third-item.mouseup",
            "body.mouseup",
        ]).toVerifySteps();

        // Drag, move & cancel
        drag("#first-item").moveTo("#third-item").cancel();

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",

            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "third-item.pointerenter",
            "third-item.mouseenter",

            // Cancel
            "body.keydown",
            "body.keyup",
        ]).toVerifySteps();

        // Drag, move & drop
        drag("#first-item").moveTo("#third-item").drop();

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",

            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "third-item.pointerenter",
            "third-item.mouseenter",

            // Drop
            "third-item.pointerup",
            "body.pointerup",
            "third-item.mouseup",
            "body.mouseup",
        ]).toVerifySteps();

        // Drag, move & drop (different target)
        drag("#first-item").moveTo("#second-item").drop("#third-item");

        expect([
            // Drag first
            "first-item.pointerdown",
            "body.pointerdown",
            "first-item.mousedown",
            "body.mousedown",

            // Move to second
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "second-item.pointerenter",
            "second-item.mouseenter",

            // Move to third
            "first-item.pointermove",
            "body.pointermove",
            "first-item.mousemove",
            "body.mousemove",
            "third-item.pointerenter",
            "third-item.mouseenter",

            // Drop
            "third-item.pointerup",
            "body.pointerup",
            "third-item.mouseup",
            "body.mouseup",
        ]).toVerifySteps();
    });

    test.tags`no focus`("fill: text", async () => {
        await mount(/* xml */ `<input type="text" value="" />`);
        monitorEvents("input");

        expect("input").not.toHaveValue();
        expect([]).toVerifySteps();

        click("input");
        fill("Test value");

        expect("input").toHaveValue("Test value");
        expect([
            // Click
            "input.pointerdown",
            "input.mousedown",
            "input.focus",
            "input.pointerup",
            "input.mouseup",
            "input.click",
            // Fill
            ...[..."Test value"].flatMap(() => [
                "input.keydown",
                "input.input",
                "input.keyup",
            ]),
        ]).toVerifySteps();
    });

    test("fill: text with previous value", async () => {
        await mount(/* xml */ `<input type="text" value="Test" />`);

        expect("input").toHaveValue("Test");

        click("input");
        fill(" value");

        expect("input").toHaveValue("Test value");
    });

    test("fill: number", async () => {
        await mount(/* xml */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        click("input");
        fill(42);

        expect("input").toHaveValue(42);
    });

    test("fill: email", async () => {
        await mount(/* xml */ `<input type="email" />`);

        expect("input").not.toHaveValue();

        click("input");
        fill("john@doe.com");

        expect("input").toHaveValue("john@doe.com");
    });

    test("setInputFiles: single file", async () => {
        await mount(/* xml */ `<input type="file" />`);
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
        await mount(/* xml */ `<input type="file" multiple="multiple" />`);
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
        await mount(/* xml */ `
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
        await mount(/* xml */ `
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

    test("hover", async () => {
        await mount(/* xml */ `<button type="button">Click me</button>`);
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
    });

    test.tags`no focus`("keyDown", async () => {
        await mount(/* xml */ `<input type="text" />`);
        monitorEvents("input");

        click("input");
        keyDown("a");

        expect([
            // Click
            "input.pointerdown",
            "input.mousedown",
            "input.focus",
            "input.pointerup",
            "input.mouseup",
            "input.click",
            // Key down
            "input.keydown",
            "input.input",
        ]).toVerifySteps();

        keyUp("a");

        expect("input").toHaveValue("a");
        expect(["input.keyup"]).toVerifySteps();
    });

    test("leave", async () => {
        await mount(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        leave("button");

        expect([
            "button.pointermove",
            "button.mousemove",
            "button.pointerout",
            "button.mouseout",
            "button.pointerleave",
            "button.mouseleave",
        ]).toVerifySteps();
    });

    test.tags`no focus`("pointerDown", async () => {
        await mount(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        pointerDown("button");

        expect(["button.pointerdown", "button.mousedown", "button.focus"]).toVerifySteps();

        pointerUp("button");

        expect(["button.pointerup", "button.mouseup", "button.click"]).toVerifySteps();
    });

    test.tags`no focus`("press key on text input", async () => {
        await mount(/* xml */ `<input type="text" />`);
        monitorEvents("input");

        click("input");
        press("a");

        expect("input").toHaveValue("a");
        expect([
            // Click
            "input.pointerdown",
            "input.mousedown",
            "input.focus",
            "input.pointerup",
            "input.mouseup",
            "input.click",
            // Key press
            "input.keydown",
            "input.input",
            "input.keyup",
        ]).toVerifySteps();
    });

    test("press key on number input", async () => {
        await mount(/* xml */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        click("input");
        press("4");

        expect("input").toHaveValue(4);

        press("2");

        expect("input").toHaveValue(42);
    });

    test.tags`no focus`("press 'Enter' on form input", async () => {
        await mount(/* xml */ `
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

    test.tags`no focus`("press 'Enter' on form button", async () => {
        await mount(/* xml */ `
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

    test.tags`no focus`("press 'Enter' on form submit button", async () => {
        await mount(/* xml */ `
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

    test.tags`no focus`("press 'Space' on checkbox input", async () => {
        await mount(/* xml */ `<input type="checkbox" checked="" />`);
        monitorEvents("input");

        expect("input").toHaveProperty("checked", true);

        uncheck("input"); // true -> false

        expect("input").toHaveProperty("checked", false);

        press(" "); // false -> true

        expect("input").toHaveProperty("checked", true);
        expect([
            // Click
            "input.pointerdown",
            "input.mousedown",
            "input.focus",
            "input.pointerup",
            "input.mouseup",
            "input.click",
            "input.input",
            "input.change",
            // Key press
            "input.keydown",
            "input.input",
            "input.keyup",
            // Click triggered by key press
            "input.click",
            "input.input",
            "input.change",
        ]).toVerifySteps();
    });

    test("press 'Backspace' on number input", async () => {
        await mount(/* xml */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        click("input");
        press("Backspace");

        expect("input").toHaveValue(42);

        press("Backspace");

        expect("input").toHaveValue(4);
    });

    test("special keys modifiers: Windows", async () => {
        mockUserAgent("Windows");

        await mount(/* xml */ `<input />`);

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
        mockUserAgent("Macintosh");

        await mount(/* xml */ `<input />`);

        click("input");

        monitorEvents("input", formatKeyBoardEvent);

        press("alt");

        expect(["keydown:Alt.ctrl", "keyup:Alt.ctrl"]).toVerifySteps();

        press("ctrl");

        expect(["keydown:Control.meta", "keyup:Control.meta"]).toVerifySteps();

        press("meta");

        expect(["keydown:Meta.meta", "keyup:Meta.meta"]).toVerifySteps();

        press("shift");

        expect(["keydown:Shift.shift", "keyup:Shift.shift"]).toVerifySteps();
    });

    test("compose shift, alt and control and a key", async () => {
        await mount(/* xml */ `<input />`);

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
        await mount(/* xml */ `
            <div class="scrollable" style="height: 200px; width: 200px; overflow: auto;">
                <div style="height: 2000px; width: 2000px;"></div>
            </div>
        `);

        scroll(".scrollable", { top: 500 });

        expect(".scrollable").toHaveProperty("scrollTop", 500);
        expect(".scrollable").toHaveProperty("scrollLeft", 0);

        scroll(".scrollable", { left: 1200 });

        expect(".scrollable").toHaveProperty("scrollTop", 500);
        expect(".scrollable").toHaveProperty("scrollLeft", 1200);
    });

    test.tags`no focus`("select", async () => {
        await mount(/* xml */ `
            <select>
                <option value="a">A</option>
                <option value="b">B</option>
                <option value="c">C</option>
            </select>
        `);
        monitorEvents("select");

        expect("select").toHaveValue("a"); // default to first option
        expect([]).toVerifySteps();

        click("select");
        select("b");

        expect("select").toHaveValue("b");
        expect([
            // Click
            "select.pointerdown",
            "select.mousedown",
            "select.focus",
            "select.pointerup",
            "select.mouseup",
            "select.click",
            // Select
            "select.change",
        ]).toVerifySteps();
    });
});
