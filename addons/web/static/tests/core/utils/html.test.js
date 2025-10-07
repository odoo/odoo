import { htmlEscape, markup } from "@odoo/owl";

const Markup = markup().constructor;

import { describe, expect, test } from "@odoo/hoot";
import {
    createDocumentFragmentFromContent,
    createElementWithContent,
    highlightText,
    htmlFormatList,
    htmlJoin,
    htmlReplace,
    htmlReplaceAll,
    htmlSprintf,
    htmlTrim,
    isHtmlEmpty,
    odoomark,
    setElementContent,
} from "@web/core/utils/html";

describe.current.tags("headless");

test("createDocumentFragmentFromContent escapes text", () => {
    const doc = createDocumentFragmentFromContent("<p>test</p>");
    expect(doc.body.innerHTML).toEqual("&lt;p&gt;test&lt;/p&gt;");
});

test("createDocumentFragmentFromContent keeps html markup", () => {
    const doc = createDocumentFragmentFromContent(markup`<p>test</p>`);
    expect(doc.body.innerHTML).toEqual("<p>test</p>");
});

test("createElementWithContent escapes text", () => {
    const res = createElementWithContent("div", "<p>test</p>");
    expect(res.outerHTML).toBe("<div>&lt;p&gt;test&lt;/p&gt;</div>");
});

test("createElementWithContent keeps html markup", () => {
    const res = createElementWithContent("div", markup`<p>test</p>`);
    expect(res.outerHTML).toBe("<div><p>test</p></div>");
});

test("highlightText", () => {
    expect(highlightText("b", "", "hl").toString()).toBe("");
    expect(highlightText("", "b", "hl").toString()).toBe("b");
    expect(highlightText("b", "abc", "hl").toString()).toBe('a<span class="hl">b</span>c');
    expect(highlightText("b", "abcb", "hl").toString()).toBe(
        'a<span class="hl">b</span>c<span class="hl">b</span>'
    );
    expect(highlightText("b", "abbc", "hl").toString()).toBe(
        'a<span class="hl">b</span><span class="hl">b</span>c'
    );
    expect(highlightText("b", "<p>ab</p>", "hl").toString()).toBe(
        '&lt;p&gt;a<span class="hl">b</span>&lt;/p&gt;'
    );
    expect(highlightText("b", markup`<p>ab</p>`, "hl").toString()).toBe(
        '<p>a<span class="hl">b</span></p>'
    );
    expect(highlightText("<", "<p>ab</p>", "hl").toString()).toBe(
        '<span class="hl">&lt;</span>p&gt;ab<span class="hl">&lt;</span>/p&gt;'
    );
    expect(highlightText("<", markup`<p>ab</p>`, "hl").toString()).toBe("<p>ab</p>");
    expect(highlightText(markup`<`, "<p>ab</p>", "hl").toString()).toBe("&lt;p&gt;ab&lt;/p&gt;");
    expect(highlightText(markup`<p>ab</p>`, markup`<p>ab</p>`, "hl").toString()).toBe(
        '<span class="hl"><p>ab</p></span>'
    );
    expect(highlightText("cè", "Cédric ce cèdre", "hl").toString()).toBe(
        '<span class="hl">Cé</span>dric <span class="hl">ce</span> <span class="hl">cè</span>dre',
        {
            message: "highlightText should be accent insensitive",
        }
    );
});

test("htmlEscape escapes text", () => {
    const res = htmlEscape("<p>test</p>");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlEscape keeps html markup", () => {
    const res = htmlEscape(markup`<p>test</p>`);
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
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

test("htmlReplace with text/text/text replaces with escaped text", () => {
    let res = htmlReplace("<p>test</p>", "<p>test</p>", "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplace("<p>test</p>", "<p>test</p>", () => "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with text/text/html replaces with html markup", () => {
    let res = htmlReplace("<p>test</p>", "<p>test</p>", markup`<span>test</span>`);
    expect(res.toString()).toBe("<span>test</span>");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplace("<p>test</p>", "<p>test</p>", () => markup`<span>test</span>`);
    expect(res.toString()).toBe("<span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with text/html does not find", () => {
    let res = htmlReplace("<p>test</p>", markup`<p>test</p>`, "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplace("<p>test</p>", () => markup`<p>test</p>`, "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/html/html replaces with html markup", () => {
    let res = htmlReplace(markup`<p>test</p>`, markup`<p>test</p>`, markup`<span>test</span>`);
    expect(res.toString()).toBe("<span>test</span>");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplace(markup`<p>test</p>`, markup`<p>test</p>`, () => markup`<span>test</span>`);
    expect(res.toString()).toBe("<span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/html/text replaces with escaped text", () => {
    let res = htmlReplace(markup`<p>test</p>`, markup`<p>test</p>`, "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplace(markup`<p>test</p>`, markup`<p>test</p>`, () => "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/text does not find", () => {
    let res = htmlReplace(markup`<p>test</p>`, "<p>test</p>", "never found");
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplace(markup`<p>test</p>`, () => "<p>test</p>", "never found");
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with text/text/text replaces all with escaped text", () => {
    let res = htmlReplaceAll("<p>test</p> <p>test</p>", "<p>test</p>", "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplaceAll("<p>test</p> <p>test</p>", "<p>test</p>", () => "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with text/text/html replaces all with html markup", () => {
    let res = htmlReplaceAll("<p>test</p> <p>test</p>", "<p>test</p>", markup`<span>test</span>`);
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplaceAll("<p>test</p> <p>test</p>", "<p>test</p>", () => markup`<span>test</span>`);
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with text/html does not find, escapes all", () => {
    let res = htmlReplaceAll("<p>test</p> <p>test</p>", markup`<p>test</p>`, "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplaceAll("<p>test</p> <p>test</p>", markup`<p>test</p>`, () => "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with html/html/html replaces all with html markup", () => {
    let res = htmlReplaceAll(
        markup`<p>test</p> <p>test</p>`,
        markup`<p>test</p>`,
        markup`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplaceAll(
        markup`<p>test</p> <p>test</p>`,
        markup`<p>test</p>`,
        () => markup`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with html/html/text replaces all with escaped text", () => {
    let res = htmlReplaceAll(
        markup`<p>test</p> <p>test</p>`,
        markup`<p>test</p>`,
        "<span>test</span>"
    );
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplaceAll(
        markup`<p>test</p> <p>test</p>`,
        markup`<p>test</p>`,
        () => "<span>test</span>"
    );
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplaceAll with html/text does not find, keeps all", () => {
    let res = htmlReplaceAll(markup`<p>test</p> <p>test</p>`, "<p>test</p>", "never found");
    expect(res.toString()).toBe("<p>test</p> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);

    res = htmlReplaceAll(markup`<p>test</p> <p>test</p>`, "<p>test</p>", () => "never found");
    expect(res.toString()).toBe("<p>test</p> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace/htmlReplaceAll only accept functions replacement when search is a RegExp", () => {
    expect(() => htmlReplace("test", /test/, "$1")).toThrow(
        "htmlReplace: replacement must be a function when search is a RegExp."
    );
    expect(() => htmlReplaceAll("test", /test/, "$1")).toThrow(
        "htmlReplaceAll: replacement must be a function when search is a RegExp."
    );
});

test("htmlTrim escapes text", () => {
    const res = htmlTrim(" <p>test</p> ");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlTrim keeps html markup", () => {
    const res = htmlTrim(markup` <p>test</p> `);
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("odoomark", () => {
    expect(odoomark("").toString()).toBe("");
    expect(odoomark("**test**").toString()).toBe("<b>test</b>");
    expect(odoomark("**test** something else **test**").toString()).toBe(
        "<b>test</b> something else <b>test</b>"
    );
    expect(odoomark("--test--").toString()).toBe("<span class='text-muted'>test</span>");
    expect(odoomark("--test-- something else --test--").toString()).toBe(
        "<span class='text-muted'>test</span> something else <span class='text-muted'>test</span>"
    );
    expect(odoomark("`test`").toString()).toBe(
        `<span class="o_tag position-relative d-inline-flex align-items-center mw-100 o_badge badge rounded-pill lh-1 o_tag_color_0">test</span>`
    );
    expect(odoomark("`test` something else `test`").toString()).toBe(
        `<span class="o_tag position-relative d-inline-flex align-items-center mw-100 o_badge badge rounded-pill lh-1 o_tag_color_0">test</span> something else <span class="o_tag position-relative d-inline-flex align-items-center mw-100 o_badge badge rounded-pill lh-1 o_tag_color_0">test</span>`
    );
    expect(odoomark("test\ttest2").toString()).toBe(
        `test<span style="margin-left: 2em"></span>test2`
    );
    expect(odoomark("test\ntest2").toString()).toBe("test<br/>test2");
    expect(odoomark("<p>**test**</p>").toString()).toBe("&lt;p&gt;<b>test</b>&lt;/p&gt;");
    expect(odoomark(markup`<p>**test**</p>`).toString()).toBe("<p><b>test</b></p>");
});
