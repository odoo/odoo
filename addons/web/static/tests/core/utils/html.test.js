import { markup } from "@odoo/owl";

const Markup = markup().constructor;

import { describe, expect, test } from "@odoo/hoot";
import {
    createElementWithContent,
    htmlFormatList,
    htmlJoin,
    htmlSprintf,
    isHtmlEmpty,
    setElementContent,
} from "@web/core/utils/html";

describe.current.tags("headless");

test("createElementWithContent escapes text", () => {
    const res = createElementWithContent("div", "<p>test</p>");
    expect(res.outerHTML).toBe("<div>&lt;p&gt;test&lt;/p&gt;</div>");
});

test("createElementWithContent keeps html markup", () => {
    const res = createElementWithContent("div", markup`<p>test</p>`);
    expect(res.outerHTML).toBe("<div><p>test</p></div>");
});

test("htmlJoin keeps html markup and escapes text", () => {
    const res = htmlJoin([markup`<p>test</p>`, "<p>test</p>"]);
    expect(res.toString()).toBe("<p>test</p>&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlJoin escapes text separator", () => {
    const res = htmlJoin(["a", "b"], "<br>");
    expect(res.toString()).toBe("a&lt;br&gt;b");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlJoin keeps html separator", () => {
    const res = htmlJoin(["a", "b"], markup`<br>`);
    expect(res.toString()).toBe("a<br>b");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlSprintf escapes str with list params", () => {
    const res = htmlSprintf("<p>%s</p>", "Hi");
    expect(res.toString()).toBe("&lt;p&gt;Hi&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlSprintf escapes list params", () => {
    const res = htmlSprintf(
        markup`<p>%s</p>%s`,
        markup`<span>test 1</span>`,
        `<span>test 2</span>`
    );
    expect(res.toString()).toBe(
        "<p><span>test 1</span>,&lt;span&gt;test 2&lt;/span&gt;</p>undefined"
    );
    expect(res).toBeInstanceOf(Markup);
});

test("htmlSprintf escapes str with object params", () => {
    const res = htmlSprintf("<p>%(t1)s</p>", { t1: "Hi" });
    expect(res.toString()).toBe("&lt;p&gt;Hi&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlSprintf escapes object param", () => {
    const res = htmlSprintf(markup`<p>%(t1)s</p>%(t2)s`, {
        t1: `<span>test 1</span>`,
        t2: markup`<span>test 2</span>`,
    });
    expect(res.toString()).toBe("<p>&lt;span&gt;test 1&lt;/span&gt;</p><span>test 2</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("isHtmlEmpty does not consider text as empty", () => {
    expect(isHtmlEmpty("<p></p>")).toBe(false);
});

test("isHtmlEmpty considers empty html markup as empty", () => {
    expect(isHtmlEmpty(markup`<p></p>`)).toBe(true);
});

test("setElementContent escapes text", () => {
    const div = document.createElement("div");
    setElementContent(div, "<p>test</p>");
    expect(div.innerHTML).toBe("&lt;p&gt;test&lt;/p&gt;");
});

test("setElementContent keeps html markup", () => {
    const div = document.createElement("div");
    setElementContent(div, markup`<p>test</p>`);
    expect(div.innerHTML).toBe("<p>test</p>");
});

test("htmlFormatList", () => {
    const list = ["<p>test 1</p>", markup`<p>test 2</p>`, "&lt;p&gt;test 3&lt;/p&gt;"];
    const res = htmlFormatList(list, { localeCode: "fr-FR" });
    expect(res.toString()).toBe(
        "&lt;p&gt;test 1&lt;/p&gt;, <p>test 2</p> et &amp;lt;p&amp;gt;test 3&amp;lt;/p&amp;gt;"
    );
    expect(res).toBeInstanceOf(Markup);
});
