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
    uncheck,
} from "../../../hoot-dom/hoot-dom";
import { after, describe, expect, test } from "../../hoot";
import { mount, parseUrl } from "../local_helpers";

/**
 * @param {import("../../helpers/dom").Target} target
 */
const monitorEvents = (target) => {
    const element = queryOne(target);
    for (const prop in element) {
        const type = prop.match(/^on(\w+)/)?.[1];
        if (!type) {
            continue;
        }
        const off = on(element, type, (ev) => {
            expect.step([ev.currentTarget.tagName.toLowerCase(), ev.type].join("."));
            if (ev.type === "submit") {
                ev.preventDefault();
            }
        });
        after(off);
    }
};

describe(parseUrl(import.meta.url), () => {
    test("clear", () => {
        mount(/* html */ `<input type="text" value="Test" />`);
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

    test("clear: email", () => {
        mount(/* html */ `<input type="email" value="john@doe.com" />`);

        expect("input").toHaveValue("john@doe.com");

        click("input");
        clear();

        expect("input").toHaveValue("");
    });

    test("clear: number", () => {
        mount(/* html */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        click("input");
        clear();

        expect("input").not.toHaveValue();
    });

    test("clear: files", () => {
        mount(/* html */ `<input type="file" />`);
        const file = new File([""], "file.txt");

        expect("input").not.toHaveValue();

        click("input");
        fill(file);

        expect("input").toHaveValue([file]);

        clear();

        expect("input").not.toHaveValue();
    });

    test("click", () => {
        mount(/* html */ `<button autofocus="" type="button">Click me</button>`);
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

    test("drag", () => {
        mount(/* html */ `
            <ul class="list">
                <li class="item" draggable="true">Item 1</li>
                <li class="item" draggable="true">Item 2</li>
            </ul>
        `);
        monitorEvents(".item:first");

        const { drop } = drag(".item:first");
        drop(".item:last");

        expect([
            "li.pointerdown",
            "li.mousedown",
            "li.dragstart",
            "li.pointermove",
            "li.mousemove",
            "li.drag",
            "li.mouseenter",
        ]).toVerifySteps();
    });

    test("fill: text", () => {
        mount(/* html */ `<input type="text" value="" />`);
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
                "input.keypress",
                "input.input",
                "input.keyup",
            ]),
        ]).toVerifySteps();
    });

    test("fill: text with previous value", () => {
        mount(/* html */ `<input type="text" value="Test" />`);

        expect("input").toHaveValue("Test");

        click("input");
        fill(" value");

        expect("input").toHaveValue("Test value");
    });

    test("fill: number", () => {
        mount(/* html */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        click("input");
        fill(42);

        expect("input").toHaveValue(42);
    });

    test("fill: email", () => {
        mount(/* html */ `<input type="email" />`);

        expect("input").not.toHaveValue();

        click("input");
        fill("john@doe.com");

        expect("input").toHaveValue("john@doe.com");
    });

    test("fill: single file", () => {
        mount(/* html */ `<input type="file" />`);
        const file1 = new File([""], "file1.txt");
        const file2 = new File([""], "file2.txt");

        expect("input").not.toHaveValue();

        click("input");
        fill(file1);

        expect("input").toHaveValue(/file1\.txt/);
        expect("input").toHaveValue([file1]);

        fill(file2);

        expect("input").toHaveValue(/file2\.txt/);
        expect("input").toHaveValue([file2]);
    });

    test("fill: multiple files", () => {
        mount(/* html */ `<input type="file" multiple>`);
        const file1 = new File([""], "file1.txt");
        const file2 = new File([""], "file2.txt");

        expect("input").not.toHaveValue();

        click("input");
        fill(file1);

        expect("input").toHaveValue(/file1\.txt/);
        expect("input").toHaveValue([file1]);

        fill(file2);

        expect("input").toHaveValue([file1, file2]);
    });

    test("hover", () => {
        mount(/* html */ `<button type="button">Click me</button>`);
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

    test("keyDown", () => {
        mount(/* html */ `<input type="text" />`);
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
            "input.keypress",
            "input.input",
        ]).toVerifySteps();

        keyUp("a");

        expect("input").toHaveValue("a");
        expect(["input.keyup"]).toVerifySteps();
    });

    test("leave", () => {
        mount(/* html */ `<button type="button">Click me</button>`);
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

    test("pointerDown", () => {
        mount(/* html */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        pointerDown("button");

        expect(["button.pointerdown", "button.mousedown", "button.focus"]).toVerifySteps();

        pointerUp("button");

        expect(["button.pointerup", "button.mouseup", "button.click"]).toVerifySteps();
    });

    test("press key on text input", () => {
        mount(/* html */ `<input type="text" />`);
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
            "input.keypress",
            "input.input",
            "input.keyup",
        ]).toVerifySteps();
    });

    test("press key on number input", () => {
        mount(/* html */ `<input type="number" />`);

        expect("input").not.toHaveValue();

        click("input");
        press("4");

        expect("input").toHaveValue(4);

        press("2");

        expect("input").toHaveValue(42);
    });

    test("press 'Enter' on form input", () => {
        mount(/* html */ `
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

    test("press 'Enter' on form button", () => {
        mount(/* html */ `
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

    test("press 'Enter' on form submit button", () => {
        mount(/* html */ `
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

    test("press 'Space' on checkbox input", () => {
        mount(/* html */ `<input type="checkbox" checked="" />`);
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
            "input.keypress",
            "input.input",
            "input.keyup",
            // Click triggered by key press
            "input.click",
            "input.input",
            "input.change",
        ]).toVerifySteps();
    });

    test("press 'Backspace' on number input", () => {
        mount(/* html */ `<input type="number" value="421" />`);

        expect("input").toHaveValue(421);

        click("input");
        press("Backspace");

        expect("input").toHaveValue(42);

        press("Backspace");

        expect("input").toHaveValue(4);
    });

    test.todo("scroll", () => {
        expect(scroll()).toBeTruthy();
    });

    test("select", () => {
        mount(/* html */ `
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
