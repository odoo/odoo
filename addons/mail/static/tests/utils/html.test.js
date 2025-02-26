import { describe, expect, test } from "@odoo/hoot";
import { Markup } from "@web/core/utils/html";

describe.current.tags("headless");

test("Markup.createDocumentFragmentFromContent escapes text", () => {
    const doc = Markup.createDocumentFragmentFromContent("<p>test</p>");
    expect(doc.body.innerHTML).toEqual("&lt;p&gt;test&lt;/p&gt;");
});

test("Markup.createDocumentFragmentFromContent keeps html markup", () => {
    const doc = Markup.createDocumentFragmentFromContent(Markup.build`<p>test</p>`);
    expect(doc.body.innerHTML).toEqual("<p>test</p>");
});

test("Markup.replace with text/text/text replaces first with escaped text, escapes second", () => {
    const res = Markup.replace("<p>test</p> <p>test</p>", "<p>test</p>", "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replace with text/text/html replaces first with html markup, escapes second", () => {
    const res = Markup.replace(
        "<p>test</p> <p>test</p>",
        "<p>test</p>",
        Markup.build`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replace with text/html does not find, escapes both", () => {
    const res = Markup.replace("<p>test</p> <p>test</p>", Markup.build`<p>test</p>`, "never found");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replace with html/html/html replaces first with html markup, keeps second", () => {
    const res = Markup.replace(
        Markup.build`<p>test</p> <p>test</p>`,
        Markup.build`<p>test</p>`,
        Markup.build`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replace with html/html/text replaces first with escaped text, keeps second", () => {
    const res = Markup.replace(
        Markup.build`<p>test</p> <p>test</p>`,
        Markup.build`<p>test</p>`,
        "<span>test</span>"
    );
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replace with html/text does not find, keeps both", () => {
    const res = Markup.replace(Markup.build`<p>test</p> <p>test</p>`, "<p>test</p>", "never found");
    expect(res.toString()).toBe("<p>test</p> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replaceAll with text/text/text replaces all with escaped text", () => {
    const res = Markup.replaceAll("<p>test</p> <p>test</p>", "<p>test</p>", "<span>test</span>");
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replaceAll with text/text/html replaces all with html markup", () => {
    const res = Markup.replaceAll(
        "<p>test</p> <p>test</p>",
        "<p>test</p>",
        Markup.build`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replaceAll with text/html does not find, escapes all", () => {
    const res = Markup.replaceAll(
        "<p>test</p> <p>test</p>",
        Markup.build`<p>test</p>`,
        "never found"
    );
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt; &lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replaceAll with html/html/html replaces all with html markup", () => {
    const res = Markup.replaceAll(
        Markup.build`<p>test</p> <p>test</p>`,
        Markup.build`<p>test</p>`,
        Markup.build`<span>test</span>`
    );
    expect(res.toString()).toBe("<span>test</span> <span>test</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replaceAll with html/html/text replaces all with escaped text", () => {
    const res = Markup.replaceAll(
        Markup.build`<p>test</p> <p>test</p>`,
        Markup.build`<p>test</p>`,
        "<span>test</span>"
    );
    expect(res.toString()).toBe("&lt;span&gt;test&lt;/span&gt; &lt;span&gt;test&lt;/span&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.replaceAll with html/text does not find, keeps all", () => {
    const res = Markup.replaceAll(
        Markup.build`<p>test</p> <p>test</p>`,
        "<p>test</p>",
        "never found"
    );
    expect(res.toString()).toBe("<p>test</p> <p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.trim escapes text", () => {
    const res = Markup.trim(" <p>test</p> ");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.trim keeps html markup", () => {
    const res = Markup.trim(Markup.build` <p>test</p> `);
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});
