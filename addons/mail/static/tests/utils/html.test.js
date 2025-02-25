import {
    createDocumentFragmentFromContent,
    htmlReplace,
    htmlReplaceAll,
    htmlTrim,
} from "@mail/utils/common/html";

import { describe, expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";
import { htmlMarkup } from "@web/core/utils/html";

const Markup = markup().constructor;

describe.current.tags("headless");

test("createDocumentFragmentFromContent escapes text", () => {
    const doc = createDocumentFragmentFromContent("<p>test</p>");
    expect(doc.body.innerHTML).toEqual("&lt;p&gt;test&lt;/p&gt;");
});

test("createDocumentFragmentFromContent keeps html markup", () => {
    const doc = createDocumentFragmentFromContent(htmlMarkup`<p>test</p>`);
    expect(doc.body.innerHTML).toEqual("<p>test</p>");
});

test("htmlReplace with text/text/text replaces first with escaped text, escapes second", () => {
    const res = htmlReplace("<p>test</p> <p>test</p>", "<p>test</p>", "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with text/text/html replaces first with html markup, escapes second", () => {
    const res = htmlReplace(
        "<p>test</p> <p>test</p>",
        "<p>test</p>",
        htmlMarkup`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with text/html does not find, escapes both", () => {
    const res = htmlReplace("<p>test</p> <p>test</p>", htmlMarkup`<p>test</p>`, "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/html/html replaces first with html markup, keeps second", () => {
    const res = htmlReplace(
        htmlMarkup`<p>test</p> <p>test</p>`,
        htmlMarkup`<p>test</p>`,
        htmlMarkup`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/html/text replaces first with escaped text, keeps second", () => {
    const res = htmlReplace(
        htmlMarkup`<p>test</p> <p>test</p>`,
        htmlMarkup`<p>test</p>`,
        "<span>test</span>"
    );
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/text does not find, keeps both", () => {
    const res = htmlReplace(htmlMarkup`<p>test</p> <p>test</p>`, "<p>test</p>", "never found");
    expect(res.toString()).toBe("<p>test</p> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with text/text/text replaces all with escaped text", () => {
    const res = htmlReplaceAll("<p>test</p> <p>test</p>", "<p>test</p>", "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with text/text/html replaces all with html markup", () => {
    const res = htmlReplaceAll(
        "<p>test</p> <p>test</p>",
        "<p>test</p>",
        htmlMarkup`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with text/html does not find, escapes all", () => {
    const res = htmlReplaceAll("<p>test</p> <p>test</p>", htmlMarkup`<p>test</p>`, "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with html/html/html replaces all with html markup", () => {
    const res = htmlReplaceAll(
        htmlMarkup`<p>test</p> <p>test</p>`,
        htmlMarkup`<p>test</p>`,
        htmlMarkup`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with html/html/text replaces all with escaped text", () => {
    const res = htmlReplaceAll(
        htmlMarkup`<p>test</p> <p>test</p>`,
        htmlMarkup`<p>test</p>`,
        "<span>test</span>"
    );
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with html/text does not find, keeps all", () => {
    const res = htmlReplaceAll(htmlMarkup`<p>test</p> <p>test</p>`, "<p>test</p>", "never found");
    expect(res.toString()).toBe("<p>test</p> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlTrim escapes text", () => {
    const res = htmlTrim(" <p>test</p> ");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlTrim keeps html markup", () => {
    const res = htmlTrim(htmlMarkup` <p>test</p> `);
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});
