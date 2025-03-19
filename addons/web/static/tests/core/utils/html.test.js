import { markup } from "@odoo/owl";

const Markup = markup().constructor;

import { describe, expect, test } from "@odoo/hoot";
import {
    createElementWithContent,
    htmlEscape,
    htmlFormatList,
    isHtmlEmpty,
    setElementContent,
} from "@web/core/utils/html";

describe.current.tags("headless");

test("createElementWithContent escapes text", () => {
    const res = createElementWithContent("div", "<p>test</p>");
    expect(res.outerHTML).toBe("<div>&lt;p&gt;test&lt;/p&gt;</div>");
});

test("createElementWithContent keeps html markup", () => {
    const res = createElementWithContent("div", markup("<p>test</p>"));
    expect(res.outerHTML).toBe("<div><p>test</p></div>");
});

test("htmlEscape escapes text", () => {
    const res = htmlEscape("<p>test</p>");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlEscape keeps html markup", () => {
    const res = htmlEscape(markup("<p>test</p>"));
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("isHtmlEmpty does not consider text as empty", () => {
    expect(isHtmlEmpty("<p></p>")).toBe(false);
});

test("isHtmlEmpty considers empty html markup as empty", () => {
    expect(isHtmlEmpty(markup("<p></p>"))).toBe(true);
});

test("setElementContent escapes text", () => {
    const div = document.createElement("div");
    setElementContent(div, "<p>test</p>");
    expect(div.innerHTML).toBe("&lt;p&gt;test&lt;/p&gt;");
});

test("setElementContent keeps html markup", () => {
    const div = document.createElement("div");
    setElementContent(div, markup("<p>test</p>"));
    expect(div.innerHTML).toBe("<p>test</p>");
});

test("htmlFormatList", () => {
    const list = ["<p>test 1</p>", markup("<p>test 2</p>"), "&lt;p&gt;test 3&lt;/p&gt;"];
    const res = htmlFormatList(list, { localeCode: "fr-FR" });
    expect(res.toString()).toBe(
        "&lt;p&gt;test 1&lt;/p&gt;, <p>test 2</p> et &amp;lt;p&amp;gt;test 3&amp;lt;/p&amp;gt;"
    );
    expect(res).toBeInstanceOf(Markup);
});
