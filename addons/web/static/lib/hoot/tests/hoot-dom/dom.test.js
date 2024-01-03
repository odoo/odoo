/** @odoo-module */

import { describe, expect, test } from "@odoo/hoot";
import {
    getFixture,
    getFocusableElements,
    getNextFocusableElement,
    getParentFrame,
    getPreviousFocusableElement,
    getRect,
    isEditable,
    isEventTarget,
    isFocusable,
    isVisible,
    queryAll,
    queryAllContents,
    queryOne,
} from "@web/../lib/hoot-dom/helpers/dom";
import { click } from "@web/../lib/hoot-dom/helpers/events";
import { mount, parseUrl } from "../local_helpers";

/**
 * {@link document.querySelector} shorthand
 * @param {string} selector
 * @param {HTMLElement} [root]
 */
const $ = (selector, root) => $$(selector, root)[0] || null;

/**
 * {@link document.querySelectorAll} shorthand
 * @param {string} selector
 * @param {HTMLElement} [root]
 */
const $$ = (selector, root = getFixture()) =>
    selector ? [...root.querySelectorAll(selector)] : [];

/**
 * @param {Document} document
 * @param {HTMLElement} [root]
 * @returns {Promise<HTMLIFrameElement>}
 */
function makeIframe(document, root) {
    return new Promise((resolve) => {
        const iframe = document.createElement("iframe");
        iframe.addEventListener("load", () => resolve(iframe));
        iframe.srcdoc = "<body></body>";
        (root || document.body).appendChild(iframe);
    });
}

/**
 * @param {Partial<DOMRect>} dimensions
 * @param {string} [className]
 */
function makeSquare(dimensions, className) {
    const style = Object.entries({ width: 30, height: 30, ...dimensions })
        .map(([k, v]) => `${k}:${v}px`)
        .join(";");
    return /* xml */ `
        <div
            class="position-absolute ${className}"
            style="${style}"
        />
    `;
}

const FULL_HTML_TEMPLATE = /* xml */ `
    <header>
        <h1 class="title">Title</h1>
    </header>
    <main>
        <h5 class="title">List header</h5>
        <ul class="overflow-auto" style="max-height: 80px">
            <li class="text highlighted">First item</li>
            <li class="text">Second item</li>
            <li class="text">Last item</li>
        </ul>
        <p class="text">Paragraph with some long text</p>
        <div class="d-none">Invisible section</div>
        <svg />
        <form class="overflow-auto" style="max-width: 100px">
            <h5 class="title">Form title</h5>
            <input name="name" type="text" t-att-value="'John Doe (JOD)'" />
            <input name="email" type="email" t-att-value="'johndoe@sample.com'" />
            <select name="title" t-att-value="'mr'">
                <option selected="selected">Select an option</option>
                <option value="mr">Mr.</option>
                <option value="mrs">Mrs.</option>
            </select>
            <select name="job">
                <option selected="selected">Select an option</option>
                <option value="employer">Employer</option>
                <option value="employee">Employee</option>
            </select>
            <button type="submit">Submit</button>
            <button type="submit" disabled="disabled">Cancel</button>
        </form>
        <iframe srcdoc="&lt;p&gt;Iframe text content&lt;/p&gt;" />
    </main>
    <footer>
        <em>Footer</em>
        <button type="button">Back to top</button>
    </footer>
    `;
const SVG_URL = "http://www.w3.org/2000/svg";

describe(parseUrl(import.meta.url), () => {
    test("getFocusableElements", async () => {
        await mount(/* xml */ `
            <input class="input" />
            <div class="div" tabindex="0">aaa</div>
            <button class="disabled-button" disabled="disabled">Disabled button</button>
            <button class="button" tabindex="1">Button</button>
        `);

        expect(getFocusableElements().map((el) => el.className)).toEqual([
            "button",
            "input",
            "div",
        ]);
    });

    test("getNextFocusableElement", async () => {
        await mount(/* xml */ `
            <input class="input" />
            <div class="div" tabindex="0">aaa</div>
            <button class="disabled-button" disabled="disabled">Disabled button</button>
            <button class="button" tabindex="1">Button</button>
        `);

        click(".input");

        expect(getNextFocusableElement()).toHaveClass("div");
    });

    test("getParentFrame", async () => {
        await mount(/* xml */ `<div class="root" />`);

        const parent = await makeIframe(document, queryOne(".root"));
        const child = await makeIframe(parent.contentDocument);

        const content = child.contentDocument.createElement("div");
        child.contentDocument.body.appendChild(content);

        expect(getParentFrame(content)).toBe(child);
        expect(getParentFrame(child)).toBe(parent);
        expect(getParentFrame(parent)).toBe(null);
    });

    test("getPreviousFocusableElement", async () => {
        await mount(/* xml */ `
            <input class="input" />
            <div class="div" tabindex="0">aaa</div>
            <button class="disabled-button" disabled="disabled">Disabled button</button>
            <button class="button" tabindex="1">Button</button>
        `);

        click(".input");

        expect(getPreviousFocusableElement()).toHaveClass("button");
    });

    test("getRect", async () => {
        await mount(/* xml */ `
            <div class="root position-relative">
                ${makeSquare({ left: 10, top: 20, padding: 5 }, "target")}
            </div>
        `);

        const root = queryOne(".root");
        const { x, y } = getRect(root);
        const target = root.querySelector(".target");

        expect(getRect(target)).toEqual(new DOMRect(x + 10, y + 20, 30, 30));
        expect(getRect(queryOne(".target"), { trimPadding: true })).toEqual(
            new DOMRect(x + 15, y + 25, 20, 20)
        );
    });

    test("queryAllContents", async () => {
        await mount(FULL_HTML_TEMPLATE);

        expect(queryAllContents(".title")).toEqual(["Title", "List header", "Form title"]);
        expect(queryAllContents("footer")).toEqual(["FooterBack to top"]);
    });

    test("isEditable", async () => {
        expect(isEditable(document.createElement("input"))).toBe(true);
        expect(isEditable(document.createElement("textarea"))).toBe(true);
        expect(isEditable(document.createElement("select"))).toBe(false);

        const editableDiv = document.createElement("div");
        expect(isEditable(editableDiv)).toBe(false);
        editableDiv.setAttribute("contenteditable", "true");
        expect(isEditable(editableDiv)).toBe(true);
    });

    test("isEventTarget", async () => {
        expect(isEventTarget(window)).toBe(true);
        expect(isEventTarget(document)).toBe(true);
        expect(isEventTarget(document.body)).toBe(true);
        expect(isEventTarget(document.createElement("form"))).toBe(true);
        expect(isEventTarget(document.createElementNS(SVG_URL, "svg"))).toBe(true);
        expect(isEventTarget({})).toBe(false);
    });

    test("isFocusable", async () => {
        await mount(FULL_HTML_TEMPLATE);

        expect(isFocusable("input:first")).toBe(true);
        expect(isFocusable("li:first")).toBe(false);
    });

    test("isVisible", async () => {
        await mount(FULL_HTML_TEMPLATE);

        expect(isVisible(document)).toBe(true);
        expect(isVisible(document.body)).toBe(true);
        expect(isVisible("form")).toBe(true);
        expect(isVisible(".d-none")).toBe(false);
    });

    test("queryAll", async () => {
        await mount(FULL_HTML_TEMPLATE);

        await new Promise((resolve) => $("iframe").addEventListener("load", resolve));

        // Use as a template literal
        expect(queryAll`body`).toEqual([document.body]);
        expect(queryAll`.${"title"}`).toEqual($$(".title"));
        expect(queryAll`${"ul"}${" "}${`${"li"}`}`).toEqual($$(".title"));

        // Regular selectors
        expect(queryAll()).toEqual([]);
        expect(queryAll("body")).toEqual([document.body]);
        expect(queryAll("document")).toEqual([document.body]);
        expect(queryAll(".title")).toEqual($$(".title"));
        expect(queryAll("ul > li")).toEqual($$("ul > li"));

        // :first, :last & :eq
        expect(queryAll(".title:first")).toEqual([$$(".title").at(0)]);
        expect(queryAll(".title:last")).toEqual([$$(".title").at(-1)]);
        expect(queryAll(".title:eq(1)")).toEqual([$$(".title").at(1)]);

        // :contains (text)
        expect(queryAll(".text:contains(text)")).toEqual($$("p"));
        expect(queryAll(".text:contains(item)")).toEqual($$("li"));

        // :contains (value)
        expect(queryAll("input:contains(john)")).toEqual($$("[name=name],[name=email]"));
        expect(queryAll("input:contains(john doe)")).toEqual($$("[name=name]"));
        expect(queryAll("input:contains('John Doe (JOD)')")).toEqual($$("[name=name]"));
        expect(queryAll(`input:contains("(JOD)")`)).toEqual($$("[name=name]"));
        expect(queryAll("input:contains(johndoe)")).toEqual($$("[name=email]"));
        expect(queryAll("select:contains(mr)")).toEqual($$("[name=title]"));
        expect(queryAll("select:contains(unknown value)")).toEqual([]);

        // :selected
        expect(queryAll("option:selected")).toEqual(
            $$("select[name=title] option[value=mr],select[name=job] option:first-child")
        );

        // :iframe
        expect(queryAll("iframe p:contains(text)")).toEqual([]);
        expect(queryAll(":iframe p:contains(text)")).toEqual($$("p", $("iframe").contentDocument));

        // Advanced selectors
        expect(
            queryAll(
                `main:first-of-type:contains(List header) > form:contains(Form title):nth-child(6).overflow-auto:visible select[name=job] option:selected`
            )
        ).toEqual($$("select[name=job] option:first-child"));
        expect(queryAll(`select:not(:has(:contains(Employer)))`)).toEqual($$("select[name=title]"));
    });

    test("queryOne", async () => {
        await mount(FULL_HTML_TEMPLATE);

        expect(queryOne(".title:first")).toBe($("header .title"));

        expect(() => queryOne(".title")).toThrow();
        expect(() => queryOne(".title", { exact: 2 })).toThrow();
    });
});
