/** @odoo-module */

import { after, describe, expect, test } from "@odoo/hoot";
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
} from "@odoo/hoot-dom";
import { mount, parseUrl } from "../local_helpers";

/**
 * @param {import("../../helpers/dom").Target} target
 */
const monitorEvents = (target) => {
    const element = queryOne(target);
    for (const prop in element) {
        if (prop.startsWith("on")) {
            after(
                on(element, prop.slice(2), (ev) =>
                    expect.step([ev.currentTarget.tagName.toLowerCase(), ev.type].join("."))
                )
            );
        }
    }
};

describe(parseUrl(import.meta.url), () => {
    test("clear", async () => {
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
            "input.keypress",
            "input.keyup",
            "input.input",
            "input.change",
        ]).toVerifySteps();
    });

    test("click", async () => {
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

    test("drag", async () => {
        await mount(/* xml */ `
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

    test("fill", async () => {
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
                "input.keypress",
                "input.keyup",
                "input.input",
            ]),
            "input.change",
        ]).toVerifySteps();
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

    test("keyDown", async () => {
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
            "input.keypress",
        ]).toVerifySteps();

        keyUp("a");

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

    test("pointerDown", async () => {
        await mount(/* xml */ `<button type="button">Click me</button>`);
        monitorEvents("button");

        pointerDown("button");

        expect(["button.pointerdown", "button.mousedown", "button.focus"]).toVerifySteps();

        pointerUp("button");

        expect(["button.pointerup", "button.mouseup"]).toVerifySteps();
    });

    test("press key on text input", async () => {
        await mount(/* xml */ `<input type="text" />`);
        monitorEvents("input");

        click("input");
        press("a");

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
            "input.keyup",
        ]).toVerifySteps();
    });

    test("press 'Enter' on form input", async () => {
        await mount(/* xml */ `
            <form t-on-submit.prevent="">
                <input type="text" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("input");

        expect("body").toBeFocused();

        press("Tab");

        expect("input").toBeFocused();

        press("Enter");

        expect([
            // Tab
            "input.focus",
            // Enter
            "input.keydown",
            "form.keydown",
            "input.keypress",
            "form.keypress",
            "input.keyup",
            "form.keyup",
            // Form submit
            "form.submit",
        ]).toVerifySteps();
    });

    test("press 'Enter' on form button", async () => {
        await mount(/* xml */ `
            <form t-on-submit.prevent="">
                <button type="button" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("button");

        expect("body").toBeFocused();

        press("Tab");

        expect("button").toBeFocused();

        press("Enter");

        expect([
            // Tab
            "button.focus",
            // Enter
            "button.keydown",
            "form.keydown",
            "button.keypress",
            "form.keypress",
            "button.keyup",
            "form.keyup",
            // Click triggered by Enter
            "button.click",
            "form.click",
        ]).toVerifySteps();
    });

    test("press 'Enter' on form submit button", async () => {
        await mount(/* xml */ `
            <form t-on-submit.prevent="">
                <button type="submit" />
            </form>
        `);
        monitorEvents("form");
        monitorEvents("button");

        expect("body").toBeFocused();

        press("Tab");

        expect("button").toBeFocused();

        press("Enter");

        expect([
            // Tab
            "button.focus",
            // Enter
            "button.keydown",
            "form.keydown",
            "button.keypress",
            "form.keypress",
            "button.keyup",
            "form.keyup",
            // Form submit
            "form.submit",
        ]).toVerifySteps();
    });

    test("press 'Space' on checkbox input", async () => {
        await mount(/* xml */ `<input type="checkbox" checked="" />`);
        monitorEvents("input");

        expect("input").toHaveProperty("checked", true);

        click("input"); // true -> false

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
            // Key press
            "input.input",
            "input.change",
            "input.keydown",
            "input.keypress",
            "input.keyup",
            // Click triggered by key press
            "input.click",
            "input.input",
            "input.change",
        ]).toVerifySteps();
    });

    test.skip("scroll", async () => {
        expect(scroll()).toBeTruthy();
    });

    test("select", async () => {
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
