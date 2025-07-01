/** @odoo-module */

import { describe, expect, getFixture, test } from "@odoo/hoot";
import {
    animationFrame,
    click,
    formatXml,
    getActiveElement,
    getFocusableElements,
    getNextFocusableElement,
    getPreviousFocusableElement,
    isDisplayed,
    isEditable,
    isFocusable,
    isInDOM,
    isVisible,
    queryAll,
    queryAllRects,
    queryAllTexts,
    queryFirst,
    queryOne,
    queryRect,
    waitFor,
    waitForNone,
} from "@odoo/hoot-dom";
import { mockTouch } from "@odoo/hoot-mock";
import { getParentFrame } from "@web/../lib/hoot-dom/helpers/dom";
import { mountForTest, parseUrl } from "../local_helpers";

const $ = queryFirst;
const $1 = queryOne;
const $$ = queryAll;

/**
 * @param {...string} queryAllSelectors
 */
const expectSelector = (...queryAllSelectors) => {
    /**
     * @param {string} nativeSelector
     */
    const toEqualNodes = (nativeSelector, options) => {
        if (typeof nativeSelector !== "string") {
            throw new Error(`Invalid selector: ${nativeSelector}`);
        }
        let root = options?.root || getFixture();
        if (typeof root === "string") {
            root = getFixture().querySelector(root);
            if (root.tagName === "IFRAME") {
                root = root.contentDocument;
            }
        }
        let nodes = nativeSelector ? [...root.querySelectorAll(nativeSelector)] : [];
        if (Number.isInteger(options?.index)) {
            nodes = [nodes.at(options.index)];
        }

        const selector = queryAllSelectors.join(", ");
        const fnNodes = $$(selector);
        expect(fnNodes).toEqual($$`${selector}`, {
            message: `should return the same result from a tagged template literal`,
        });
        expect(fnNodes).toEqual(nodes, {
            message: `should match ${nodes.length} nodes`,
        });
    };

    return { toEqualNodes };
};

/**
 * @param {Document} document
 * @param {HTMLElement} [root]
 * @returns {Promise<HTMLIFrameElement>}
 */
const makeIframe = (document, root) =>
    new Promise((resolve) => {
        const iframe = document.createElement("iframe");
        iframe.addEventListener("load", () => resolve(iframe));
        iframe.srcdoc = "<body></body>";
        (root || document.body).appendChild(iframe);
    });

const FULL_HTML_TEMPLATE = /* html */ `
    <header>
        <h1 class="title">Title</h1>
    </header>
    <main id="custom-html">
        <h5 class="title">List header</h5>
        <ul colspan="1" class="overflow-auto" style="max-height: 80px">
            <li class="text highlighted">First item</li>
            <li class="text">Second item</li>
            <li class="text">Last item</li>
        </ul>
        <p colspan="2" class="text">
            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Curabitur justo
            velit, tristique vitae neque a, faucibus mollis dui. Aliquam iaculis
            sodales mi id posuere. Proin malesuada bibendum pellentesque. Phasellus
            mattis at massa quis gravida. Morbi luctus interdum mi, quis dapibus
            augue. Vivamus condimentum nunc mi, vitae suscipit turpis dictum nec.
            Sed varius diam dui, eget ultricies ante dictum ac.
        </p>
        <div class="hidden" style="display: none;">Invisible section</div>
        <svg></svg>
        <form class="overflow-auto" style="max-width: 100px">
            <h5 class="title">Form title</h5>
            <input name="name" type="text" value="John Doe (JOD)" />
            <input name="email" type="email" value="johndoe@sample.com" />
            <select name="title" value="mr">
                <option>Select an option</option>
                <option value="mr" selected="selected">Mr.</option>
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
        <iframe srcdoc="&lt;p&gt;Iframe text content&lt;/p&gt;"></iframe>
    </main>
    <footer>
        <em>Footer</em>
        <button type="button">Back to top</button>
    </footer>
    `;

customElements.define(
    "hoot-test-shadow-root",
    class ShadowRoot extends HTMLElement {
        constructor() {
            super();
            const shadow = this.attachShadow({ mode: "open" });

            const p = document.createElement("p");
            p.textContent = "Shadow content";

            const input = document.createElement("input");

            shadow.append(p, input);
        }
    }
);

describe.tags("ui");
describe(parseUrl(import.meta.url), () => {
    test("formatXml", () => {
        expect(formatXml("")).toBe("");
        expect(formatXml("<input />")).toBe("<input/>");
        expect(
            formatXml(/* xml */ `
            <div>
                A
            </div>
        `)
        ).toBe(`<div>\n    A\n</div>`);
        expect(formatXml(/* xml */ `<div>A</div>`)).toBe(`<div>\n    A\n</div>`);

        // Inline
        expect(
            formatXml(
                /* xml */ `
            <div>
                A
            </div>
        `,
                { keepInlineTextNodes: true }
            )
        ).toBe(`<div>\n    A\n</div>`);
        expect(formatXml(/* xml */ `<div>A</div>`, { keepInlineTextNodes: true })).toBe(
            `<div>A</div>`
        );
    });

    test("getActiveElement", async () => {
        await mountForTest(/* xml */ `<iframe srcdoc="&lt;input &gt;"></iframe>`);

        expect(":iframe input").not.toBeFocused();

        const input = $1(":iframe input");
        await click(input);

        expect(":iframe input").toBeFocused();
        expect(getActiveElement()).toBe(input);
    });

    test("getActiveElement: shadow dom", async () => {
        await mountForTest(/* xml */ `<hoot-test-shadow-root />`);

        expect("hoot-test-shadow-root:shadow input").not.toBeFocused();

        const input = $1("hoot-test-shadow-root:shadow input");
        await click(input);

        expect("hoot-test-shadow-root:shadow input").toBeFocused();
        expect(getActiveElement()).toBe(input);
    });

    test("getFocusableElements", async () => {
        await mountForTest(/* xml */ `
            <input class="input" />
            <div class="div" tabindex="0">aaa</div>
            <span class="span" tabindex="-1">aaa</span>
            <button class="disabled-button" disabled="disabled">Disabled button</button>
            <button class="button" tabindex="1">Button</button>
        `);

        expect(getFocusableElements().map((el) => el.className)).toEqual([
            "button",
            "span",
            "input",
            "div",
        ]);

        expect(getFocusableElements({ tabbable: true }).map((el) => el.className)).toEqual([
            "button",
            "input",
            "div",
        ]);
    });

    test("getNextFocusableElement", async () => {
        await mountForTest(/* xml */ `
            <input class="input" />
            <div class="div" tabindex="0">aaa</div>
            <button class="disabled-button" disabled="disabled">Disabled button</button>
            <button class="button" tabindex="1">Button</button>
        `);

        await click(".input");

        expect(getNextFocusableElement()).toHaveClass("div");
    });

    test("getParentFrame", async () => {
        await mountForTest(/* xml */ `
            <div class="root"></div>
        `);

        const parent = await makeIframe(document, $1(".root"));
        const child = await makeIframe(parent.contentDocument);

        const content = child.contentDocument.createElement("div");
        child.contentDocument.body.appendChild(content);

        expect(getParentFrame(content)).toBe(child);
        expect(getParentFrame(child)).toBe(parent);
        expect(getParentFrame(parent)).toBe(null);
    });

    test("getPreviousFocusableElement", async () => {
        await mountForTest(/* xml */ `
            <input class="input" />
            <div class="div" tabindex="0">aaa</div>
            <button class="disabled-button" disabled="disabled">Disabled button</button>
            <button class="button" tabindex="1">Button</button>
        `);

        await click(".input");

        expect(getPreviousFocusableElement()).toHaveClass("button");
    });

    test("isEditable", async () => {
        expect(isEditable(document.createElement("input"))).toBe(true);
        expect(isEditable(document.createElement("textarea"))).toBe(true);
        expect(isEditable(document.createElement("select"))).toBe(false);

        const editableDiv = document.createElement("div");
        expect(isEditable(editableDiv)).toBe(false);
        editableDiv.setAttribute("contenteditable", "true");
        expect(isEditable(editableDiv)).toBe(false); // not supported
    });

    test("isFocusable", async () => {
        await mountForTest(FULL_HTML_TEMPLATE);

        expect(isFocusable("input:first")).toBe(true);
        expect(isFocusable("li:first")).toBe(false);
    });

    test("isInDom", async () => {
        await mountForTest(FULL_HTML_TEMPLATE);

        expect(isInDOM(document)).toBe(true);
        expect(isInDOM(document.body)).toBe(true);
        expect(isInDOM(document.head)).toBe(true);
        expect(isInDOM(document.documentElement)).toBe(true);

        const form = $1`form`;
        expect(isInDOM(form)).toBe(true);

        form.remove();

        expect(isInDOM(form)).toBe(false);

        const paragraph = $1`:iframe p`;
        expect(isInDOM(paragraph)).toBe(true);

        paragraph.remove();

        expect(isInDOM(paragraph)).toBe(false);
    });

    test("isDisplayed", async () => {
        await mountForTest(FULL_HTML_TEMPLATE);

        expect(isDisplayed(document)).toBe(true);
        expect(isDisplayed(document.body)).toBe(true);
        expect(isDisplayed(document.head)).toBe(true);
        expect(isDisplayed(document.documentElement)).toBe(true);
        expect(isDisplayed("form")).toBe(true);

        expect(isDisplayed(".hidden")).toBe(false);
        expect(isDisplayed("body")).toBe(false); // not available from fixture
    });

    test("isVisible", async () => {
        await mountForTest(FULL_HTML_TEMPLATE + "<hoot-test-shadow-root />");

        expect(isVisible(document)).toBe(true);
        expect(isVisible(document.body)).toBe(true);
        expect(isVisible(document.head)).toBe(false);
        expect(isVisible(document.documentElement)).toBe(true);
        expect(isVisible("form")).toBe(true);
        expect(isVisible("hoot-test-shadow-root:shadow input")).toBe(true);

        expect(isVisible(".hidden")).toBe(false);
        expect(isVisible("body")).toBe(false); // not available from fixture
    });

    test("matchMedia", async () => {
        // Invalid syntax
        expect(matchMedia("aaaa").matches).toBe(false);
        expect(matchMedia("display-mode: browser").matches).toBe(false);

        // Does not exist
        expect(matchMedia("(a)").matches).toBe(false);
        expect(matchMedia("(a: b)").matches).toBe(false);

        // Defaults
        expect(matchMedia("(display-mode:browser)").matches).toBe(true);
        expect(matchMedia("(display-mode: standalone)").matches).toBe(false);
        expect(matchMedia("not (display-mode: standalone)").matches).toBe(true);
        expect(matchMedia("(prefers-color-scheme :light)").matches).toBe(true);
        expect(matchMedia("(prefers-color-scheme : dark)").matches).toBe(false);
        expect(matchMedia("not (prefers-color-scheme: dark)").matches).toBe(true);
        expect(matchMedia("(prefers-reduced-motion: reduce)").matches).toBe(true);
        expect(matchMedia("(prefers-reduced-motion: no-preference)").matches).toBe(false);

        // Touch feature
        expect(window.matchMedia("(pointer: coarse)").matches).toBe(false);
        expect(window.ontouchstart).toBe(undefined);

        mockTouch(true);

        expect(window.matchMedia("(pointer: coarse)").matches).toBe(true);
        expect(window.ontouchstart).not.toBe(undefined);
    });

    test("waitFor: already in fixture", async () => {
        await mountForTest(FULL_HTML_TEMPLATE);

        waitFor(".title").then((el) => {
            expect.step(el.className);
            return el;
        });

        expect.verifySteps([]);

        await animationFrame();

        expect.verifySteps(["title"]);
    });

    test("waitFor: rejects", async () => {
        await expect(waitFor("never", { timeout: 1 })).rejects.toThrow(
            `expected at least 1 element after 1ms and found 0 elements: 0 matching "never"`
        );
    });

    test("waitFor: add new element", async () => {
        const el1 = document.createElement("div");
        el1.className = "new-element";

        const el2 = document.createElement("div");
        el2.className = "new-element";

        const promise = waitFor(".new-element").then((el) => {
            expect.step(el.className);
            return el;
        });

        await animationFrame();

        expect.verifySteps([]);

        getFixture().append(el1, el2);

        await expect(promise).resolves.toBe(el1);

        expect.verifySteps(["new-element"]);
    });

    test("waitForNone: DOM empty", async () => {
        waitForNone(".title").then(() => expect.step("none"));
        expect.verifySteps([]);

        await animationFrame();

        expect.verifySteps(["none"]);
    });

    test("waitForNone: rejects", async () => {
        await mountForTest(FULL_HTML_TEMPLATE);

        await expect(waitForNone(".title", { timeout: 1 })).rejects.toThrow();
    });

    test("waitForNone: delete elements", async () => {
        await mountForTest(FULL_HTML_TEMPLATE);

        waitForNone(".title").then(() => expect.step("none"));
        expect(".title").toHaveCount(3);

        for (const title of $$(".title")) {
            expect.verifySteps([]);

            title.remove();

            await animationFrame();
        }

        expect.verifySteps(["none"]);
    });

    describe("query", () => {
        test("native selectors", async () => {
            await mountForTest(FULL_HTML_TEMPLATE);

            expect($$()).toEqual([]);
            for (const selector of [
                "main",
                `.${"title"}`,
                `${"ul"}${" "}${`${"li"}`}`,
                ".title",
                "ul > li",
                "form:has(.title:not(.haha)):not(.huhu) input[name='email']:enabled",
                "[colspan='1']",
            ]) {
                expectSelector(selector).toEqualNodes(selector);
            }
        });

        test("custom pseudo-classes", async () => {
            await mountForTest(FULL_HTML_TEMPLATE);

            // :first, :last, :only & :eq
            expectSelector(".title:first").toEqualNodes(".title", { index: 0 });
            expectSelector(".title:last").toEqualNodes(".title", { index: -1 });
            expectSelector(".title:eq(-1)").toEqualNodes(".title", { index: -1 });
            expectSelector("main:only").toEqualNodes("main");
            expectSelector(".title:only").toEqualNodes("");
            expectSelector(".title:eq(1)").toEqualNodes(".title", { index: 1 });
            expectSelector(".title:eq('1')").toEqualNodes(".title", { index: 1 });
            expectSelector('.title:eq("1")').toEqualNodes(".title", { index: 1 });

            // :contains (text)
            expectSelector("main > .text:contains(ipsum)").toEqualNodes("p");
            expectSelector(".text:contains(/\\bL\\w+\\b\\sipsum/)").toEqualNodes("p");
            expectSelector(".text:contains(item)").toEqualNodes("li");

            // :contains (value)
            expectSelector("input:value(john)").toEqualNodes("[name=name],[name=email]");
            expectSelector("input:value(john doe)").toEqualNodes("[name=name]");
            expectSelector("input:value('John Doe (JOD)')").toEqualNodes("[name=name]");
            expectSelector(`input:value("(JOD)")`).toEqualNodes("[name=name]");
            expectSelector("input:value(johndoe)").toEqualNodes("[name=email]");
            expectSelector("select:value(mr)").toEqualNodes("[name=title]");
            expectSelector("select:value(unknown value)").toEqualNodes("");

            // :selected
            expectSelector("option:selected").toEqualNodes(
                "select[name=title] option[value=mr],select[name=job] option:first-child"
            );

            // :iframe
            expectSelector("iframe p:contains(iframe text content)").toEqualNodes("");
            expectSelector("div:iframe p").toEqualNodes("");
            expectSelector(":iframe p:contains(iframe text content)").toEqualNodes("p", {
                root: "iframe",
            });
        });

        test("advanced use cases", async () => {
            await mountForTest(FULL_HTML_TEMPLATE);

            // Comma-separated selectors
            expectSelector(":has(form:contains('Form title')),p:contains(ipsum)").toEqualNodes(
                "p,main"
            );

            // :has & :not combinations with custom pseudo-classes
            expectSelector(`select:has(:contains(Employer))`).toEqualNodes("select[name=job]");
            expectSelector(`select:not(:has(:contains(Employer)))`).toEqualNodes(
                "select[name=title]"
            );
            expectSelector(
                `main:first-of-type:not(:has(:contains(This text does not exist))):contains('List header') > form:has([name="name"]):contains("Form title"):nth-child(6).overflow-auto:visible select[name=job] option:selected`
            ).toEqualNodes("select[name=job] option:first-child");

            // :contains & commas
            expectSelector(`p:contains(velit,)`).toEqualNodes("p");
            expectSelector(`p:contains('velit,')`).toEqualNodes("p");
            expectSelector(`p:contains(", tristique")`).toEqualNodes("p");
            expectSelector(`p:contains(/\\bvelit,/)`).toEqualNodes("p");
        });

        // Whatever, at this point I'm just copying failing selectors and creating
        // fake contexts accordingly as I'm fixing them.

        test("comma-separated long selector: no match", async () => {
            await mountForTest(/* xml */ `
                <div class="o_we_customize_panel">
                    <we-customizeblock-option class="snippet-option-ImageTools">
                        <div class="o_we_so_color_palette o_we_widget_opened">
                            idk
                        </div>
                        <we-select data-name="shape_img_opt">
                            <we-toggler></we-toggler>
                        </we-select>
                    </we-customizeblock-option>
                </div>
            `);
            expectSelector(
                `.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened)) we-customizeblock-option[class='snippet-option-ImageTools'] we-select[data-name="shape_img_opt"] we-toggler`,
                `.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened)) we-customizeblock-option[class='snippet-option-ImageTools'] [title='we-select[data-name="shape_img_opt"] we-toggler']`
            ).toEqualNodes("");
        });

        test("comma-separated long selector: match first", async () => {
            await mountForTest(/* xml */ `
                <div class="o_we_customize_panel">
                    <we-customizeblock-option class="snippet-option-ImageTools">
                        <we-select data-name="shape_img_opt">
                            <we-toggler></we-toggler>
                        </we-select>
                    </we-customizeblock-option>
                </div>
            `);
            expectSelector(
                `.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened)) we-customizeblock-option[class='snippet-option-ImageTools'] we-select[data-name="shape_img_opt"] we-toggler`,
                `.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened)) we-customizeblock-option[class='snippet-option-ImageTools'] [title='we-select[data-name="shape_img_opt"] we-toggler']`
            ).toEqualNodes("we-toggler");
        });

        test("comma-separated long selector: match second", async () => {
            await mountForTest(/* xml */ `
                <div class="o_we_customize_panel">
                    <we-customizeblock-option class="snippet-option-ImageTools">
                        <div title='we-select[data-name="shape_img_opt"] we-toggler'>
                            idk
                        </div>
                    </we-customizeblock-option>
                </div>
            `);
            expectSelector(
                `.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened)) we-customizeblock-option[class='snippet-option-ImageTools'] we-select[data-name="shape_img_opt"] we-toggler`,
                `.o_we_customize_panel:not(:has(.o_we_so_color_palette.o_we_widget_opened)) we-customizeblock-option[class='snippet-option-ImageTools'] [title='we-select[data-name="shape_img_opt"] we-toggler']`
            ).toEqualNodes("div[title]");
        });

        test("comma-separated :contains", async () => {
            await mountForTest(/* xml */ `
                <div class="o_menu_sections">
                    <a class="dropdown-item">Products</a>
                </div>
                <nav class="o_burger_menu_content">
                    <ul>
                        <li data-menu-xmlid="sale.menu_product_template_action">
                            Products
                        </li>
                    </ul>
                </nav>
            `);
            expectSelector(
                `.o_menu_sections .dropdown-item:contains('Products'), nav.o_burger_menu_content li[data-menu-xmlid='sale.menu_product_template_action']`
            ).toEqualNodes(".dropdown-item,li");
        });

        test(":contains with line return", async () => {
            await mountForTest(/* xml */ `
                <span>
                    <div>Matrix (PAV11, PAV22, PAV31)</div>
                    <div>PA4: PAV41</div>
                </span>
            `);
            expectSelector(
                `span:contains("Matrix (PAV11, PAV22, PAV31)\nPA4: PAV41")`
            ).toEqualNodes("span");
        });

        test(":has(...):first", async () => {
            await mountForTest(/* xml */ `
                <a href="/web/event/1"></a>
                <a target="" href="/web/event/2">
                    <span>Conference for Architects TEST</span>
                </a>
            `);

            expectSelector(
                `a[href*="/event"]:contains("Conference for Architects TEST")`
            ).toEqualNodes("[target]");
            expectSelector(
                `a[href*="/event"]:contains("Conference for Architects TEST"):first`
            ).toEqualNodes("[target]");
        });

        test(":eq", async () => {
            await mountForTest(/* xml */ `
                <ul>
                    <li>a</li>
                    <li>b</li>
                    <li>c</li>
                </ul>
            `);

            expectSelector(`li:first:contains(a)`).toEqualNodes("li:nth-child(1)");
            expectSelector(`li:contains(a):first`).toEqualNodes("li:nth-child(1)");
            expectSelector(`li:first:contains(b)`).toEqualNodes("");
            expectSelector(`li:contains(b):first`).toEqualNodes("li:nth-child(2)");
        });

        test(":empty", async () => {
            await mountForTest(/* xml */ `
                <input class="empty" />
                <input class="value" value="value" />
            `);

            expectSelector(`input:empty`).toEqualNodes(".empty");
            expectSelector(`input:not(:empty)`).toEqualNodes(".value");
        });

        test("regular :contains", async () => {
            await mountForTest(/* xml */ `
                <div class="website_links_click_chart">
                    <div class="title">
                        0 clicks
                    </div>
                    <div class="title">
                        1 clicks
                    </div>
                    <div class="title">
                        2 clicks
                    </div>
                </div>
            `);

            expectSelector(`.website_links_click_chart .title:contains("1 clicks")`).toEqualNodes(
                ".title:nth-child(2)"
            );
        });

        test("other regular :contains", async () => {
            await mountForTest(/* xml */ `
                <ul
                    class="o-autocomplete--dropdown-menu ui-widget show dropdown-menu ui-autocomplete"
                    style="position: fixed; top: 283.75px; left: 168.938px"
                >
                    <li class="o-autocomplete--dropdown-item ui-menu-item block">
                        <a
                            href="#"
                            class="dropdown-item ui-menu-item-wrapper truncate ui-state-active"
                            >Account Tax Group Partner</a
                        >
                    </li>
                    <li
                        class="o-autocomplete--dropdown-item ui-menu-item block o_m2o_dropdown_option o_m2o_dropdown_option_search_more"
                    >
                        <a href="#" class="dropdown-item ui-menu-item-wrapper truncate"
                            >Search More...</a
                        >
                    </li>
                    <li
                        class="o-autocomplete--dropdown-item ui-menu-item block o_m2o_dropdown_option o_m2o_dropdown_option_create_edit"
                    >
                        <a href="#" class="dropdown-item ui-menu-item-wrapper truncate"
                            >Create and edit...</a
                        >
                    </li>
                </ul>
            `);

            expectSelector(`.ui-menu-item a:contains("Account Tax Group Partner")`).toEqualNodes(
                "ul li:first-child a"
            );
        });

        test(":iframe", async () => {
            await mountForTest(/* xml */ `
                <iframe srcdoc="&lt;p&gt;Iframe text content&lt;/p&gt;"></iframe>
            `);

            expectSelector(`:iframe html`).toEqualNodes("html", { root: "iframe" });
            expectSelector(`:iframe body`).toEqualNodes("body", { root: "iframe" });
            expectSelector(`:iframe head`).toEqualNodes("head", { root: "iframe" });
        });

        test(":contains with brackets", async () => {
            await mountForTest(/* xml */ `
                <div class="o_content">
                    <div class="o_field_widget" name="messages">
                        <table class="o_list_view table table-sm table-hover table-striped o_list_view_ungrouped">
                            <tbody>
                                <tr class="o_data_row">
                                    <td class="o_list_record_selector">
                                        bbb
                                    </td>
                                    <td class="o_data_cell o_required_modifier">
                                        <span>
                                            [test_trigger] Mitchell Admin
                                        </span>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `);

            expectSelector(
                `.o_content:has(.o_field_widget[name=messages]):has(td:contains(/^bbb$/)):has(td:contains(/^\\[test_trigger\\] Mitchell Admin$/))`
            ).toEqualNodes(".o_content");
        });

        test(":eq in the middle of a selector", async () => {
            await mountForTest(/* xml */ `
                <ul>
                    <li class="oe_overlay o_draggable"></li>
                    <li class="oe_overlay o_draggable"></li>
                    <li class="oe_overlay o_draggable oe_active"></li>
                    <li class="oe_overlay o_draggable"></li>
                </ul>
            `);
            expectSelector(`.oe_overlay.o_draggable:eq(2).oe_active`).toEqualNodes(
                "li:nth-child(3)"
            );
        });

        test("combinator +", async () => {
            await mountForTest(/* xml */ `
                <form class="js_attributes">
                    <input type="checkbox" />
                    <label>Steel - Test</label>
                </form>
            `);

            expectSelector(
                `form.js_attributes input:not(:checked) + label:contains(Steel - Test)`
            ).toEqualNodes("label");
        });

        test("multiple + combinators", async () => {
            await mountForTest(/* xml */ `
                <div class="s_cover">
                    <span class="o_text_highlight">
                        <span class="o_text_highlight_item">
                            <span class="o_text_highlight_path_underline" />
                        </span>
                        <br />
                        <span class="o_text_highlight_item">
                            <span class="o_text_highlight_path_underline" />
                        </span>
                    </span>
                </div>
            `);

            expectSelector(`
                .s_cover span.o_text_highlight:has(
                    .o_text_highlight_item
                    + br
                    + .o_text_highlight_item
                )
            `).toEqualNodes(".o_text_highlight");
        });

        test(":last", async () => {
            await mountForTest(/* xml */ `
                <div class="o_field_widget" name="messages">
                    <table class="o_list_view table table-sm table-hover table-striped o_list_view_ungrouped">
                        <tbody>
                            <tr class="o_data_row">
                                <td class="o_list_record_remove">
                                    <button class="btn">Remove</button>
                                </td>
                            </tr>
                            <tr class="o_data_row">
                                <td class="o_list_record_remove">
                                    <button class="btn">Remove</button>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            `);
            expectSelector(
                `.o_field_widget[name=messages] .o_data_row td.o_list_record_remove button:visible:last`
            ).toEqualNodes(".o_data_row:last-child button");
        });

        test("select :contains & :value", async () => {
            await mountForTest(/* xml */ `
                <select class="configurator_select form-select form-select-lg">
                    <option value="217" selected="">Metal</option>
                    <option value="218">Wood</option>
                </select>
            `);
            expectSelector(`.configurator_select:has(option:contains(Metal))`).toEqualNodes(
                "select"
            );
            expectSelector(`.configurator_select:has(option:value(217))`).toEqualNodes("select");
            expectSelector(`.configurator_select:has(option:value(218))`).toEqualNodes("select");
            expectSelector(`.configurator_select:value(217)`).toEqualNodes("select");
            expectSelector(`.configurator_select:value(218)`).toEqualNodes("");
            expectSelector(`.configurator_select:value(Metal)`).toEqualNodes("");
        });

        test("invalid selectors", async () => {
            await mountForTest(FULL_HTML_TEMPLATE);

            expect(() => $$`[colspan=1]`).toThrow(); // missing quotes
            expect(() => $$`[href=/]`).toThrow(); // missing quotes
            expect(
                () =>
                    $$`_o_wblog_posts_loop:has(span:has(i.fa-calendar-o):has(a[href="/blog?search=a"])):has(span:has(i.fa-search):has(a[href^="/blog?date_begin"]))`
            ).toThrow(); // nested :has statements
        });

        test("queryAllRects", async () => {
            await mountForTest(/* xml */ `
                <div style="width: 40px; height: 60px;" />
                <div style="width: 20px; height: 10px;" />
            `);

            expect(queryAllRects("div")).toEqual($$("div").map((el) => el.getBoundingClientRect()));
            expect(queryAllRects("div:first")).toEqual([new DOMRect({ width: 40, height: 60 })]);
            expect(queryAllRects("div:last")).toEqual([new DOMRect({ width: 20, height: 10 })]);
        });

        test("queryAllTexts", async () => {
            await mountForTest(FULL_HTML_TEMPLATE);

            expect(queryAllTexts(".title")).toEqual(["Title", "List header", "Form title"]);
            expect(queryAllTexts("footer")).toEqual(["FooterBack to top"]);
        });

        test("queryOne", async () => {
            await mountForTest(FULL_HTML_TEMPLATE);

            expect($1(".title:first")).toBe(getFixture().querySelector("header .title"));

            expect(() => $1(".title")).toThrow();
            expect(() => $1(".title", { exact: 2 })).toThrow();
        });

        test("queryRect", async () => {
            await mountForTest(/* xml */ `
                <div class="container">
                    <div class="rect" style="width: 40px; height: 60px;" />
                </div>
            `);

            expect(".rect").toHaveRect(".container"); // same rect as parent
            expect(".rect").toHaveRect({ width: 40, height: 60 });
            expect(queryRect(".rect")).toEqual($1(".rect").getBoundingClientRect());
            expect(queryRect(".rect")).toEqual(new DOMRect({ width: 40, height: 60 }));
        });

        test("queryRect with trimPadding", async () => {
            await mountForTest(/* xml */ `
                <div style="width: 50px; height: 70px; padding: 5px; margin: 6px" />
            `);

            expect("div").toHaveRect({ width: 50, height: 70 }); // with padding
            expect("div").toHaveRect({ width: 40, height: 60 }, { trimPadding: true });
        });

        test("not found messages", async () => {
            await mountForTest(/* xml */ `
                <div class="tralalero">
                    Tralala
                </div>
            `);

            expect(() => $("invalid:pseudo-selector")).toThrow();
            // Perform in-between valid query with custom pseudo selectors
            expect($`.modal:visible:contains('Tung Tung Tung Sahur')`).toBe(null);

            // queryOne error messages
            expect(() => $1()).toThrow(`found 0 elements instead of 1`);
            expect(() => $$([], { exact: 18 })).toThrow(`found 0 elements instead of 18`);
            expect(() => $1("")).toThrow(`found 0 elements instead of 1: 0 matching ""`);
            expect(() => $$(".tralalero", { exact: -20 })).toThrow(
                `found 1 element instead of -20: 1 matching ".tralalero"`
            );
            expect(() => $1`.tralalero:contains(Tralala):visible:scrollable:first`).toThrow(
                `found 0 elements instead of 1: 0 matching ".tralalero:contains(Tralala):visible:scrollable:first" (1 element with text "Tralala" > 1 visible element > 0 scrollable elements)`
            );
            expect(() =>
                $1(".tralalero", {
                    contains: "Tralala",
                    visible: true,
                    scrollable: true,
                    first: true,
                })
            ).toThrow(
                `found 0 elements instead of 1: 1 matching ".tralalero", including 1 element with text "Tralala", including 1 visible element, including 0 scrollable elements`
            );
        });
    });
});
