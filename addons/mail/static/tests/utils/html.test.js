import {
    createDocumentFragmentFromContent,
    htmlJoin,
    htmlReplace,
    htmlTrim,
} from "@mail/utils/common/html";

import { describe, expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";

const Markup = markup().constructor;

describe.current.tags("headless");

test("createDocumentFragmentFromContent escapes text", () => {
    const doc = createDocumentFragmentFromContent("<p>test</p>");
    expect(doc.body.innerHTML).toEqual("&lt;p&gt;test&lt;/p&gt;");
});

test("createDocumentFragmentFromContent keeps html markup", () => {
    const doc = createDocumentFragmentFromContent(markup("<p>test</p>"));
    expect(doc.body.innerHTML).toEqual("<p>test</p>");
});

test("htmlJoin keeps html markup and escapes text", () => {
    const res = htmlJoin(markup("<p>test</p>"), "<p>test</p>");
    expect(res.toString()).toBe("<p>test</p>&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with text/text/text replaces with escaped text", () => {
    const res = htmlReplace("<p>test</p>", "<p>test</p>", "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with text/text/html replaces with html markup", () => {
    const res = htmlReplace("<p>test</p>", "<p>test</p>", markup("<span>test</span>"));
    expect(res.toString()).toBe("<span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with text/html does not find", () => {
    const res = htmlReplace("<p>test</p>", markup("<p>test</p>"), "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/html/html replaces with html markup", () => {
    const res = htmlReplace(
        markup("<p>test</p>"),
        markup("<p>test</p>"),
        markup("<span>test</span>")
    );
    expect(res.toString()).toBe("<span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/html/text replaces with escaped text", () => {
    const res = htmlReplace(markup("<p>test</p>"), markup("<p>test</p>"), "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlReplace with html/text does not find", () => {
    const res = htmlReplace(markup("<p>test</p>"), "<p>test</p>", "never found");
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlTrim escapes text", () => {
    const res = htmlTrim(" <p>test</p> ");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("htmlTrim keeps html markup", () => {
    const res = htmlTrim(markup(" <p>test</p> "));
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});
