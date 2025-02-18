import { markup } from "@odoo/owl";

const Markup = markup().constructor;

import { describe, expect, test } from "@odoo/hoot";
import { htmlEscape, isHtmlEmpty, setElementContent } from "@web/core/utils/html";

describe.current.tags("headless");

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
