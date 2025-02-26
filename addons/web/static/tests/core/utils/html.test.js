import { describe, expect, test } from "@odoo/hoot";
import { Markup } from "@web/core/utils/html";

describe.current.tags("headless");

test("Markup.createElementWithContent escapes text", () => {
    const res = Markup.createElementWithContent("div", "<p>test</p>");
    expect(res.outerHTML).toBe("<div>&lt;p&gt;test&lt;/p&gt;</div>");
});

test("Markup.createElementWithContent keeps html markup", () => {
    const res = Markup.createElementWithContent("div", Markup.build`<p>test</p>`);
    expect(res.outerHTML).toBe("<div><p>test</p></div>");
});

test("Markup.escape escapes text", () => {
    const res = Markup.escape("<p>test</p>");
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.escape keeps html markup", () => {
    const res = Markup.escape(Markup.build`<p>test</p>`);
    expect(res.toString()).toBe("<p>test</p>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.escape", () => {
    expect(Markup.escape("<a>this is a link</a>").toString()).toBe(
        "&lt;a&gt;this is a link&lt;/a&gt;"
    );
    expect(Markup.escape(`<a href="https://www.odoo.com">odoo<a>`).toString()).toBe(
        `&lt;a href=&quot;https://www.odoo.com&quot;&gt;odoo&lt;a&gt;`
    );
    expect(Markup.escape(`<a href='https://www.odoo.com'>odoo<a>`).toString()).toBe(
        `&lt;a href=&#x27;https://www.odoo.com&#x27;&gt;odoo&lt;a&gt;`
    );
    expect(Markup.escape("<a href='https://www.odoo.com'>Odoo`s website<a>").toString()).toBe(
        `&lt;a href=&#x27;https://www.odoo.com&#x27;&gt;Odoo&#x60;s website&lt;a&gt;`
    );
});

test("Markup.formatList", () => {
    const list = ["<p>test 1</p>", Markup.build`<p>test 2</p>`, "&lt;p&gt;test 3&lt;/p&gt;"];
    const res = Markup.formatList(list, { localeCode: "fr-FR" });
    expect(res.toString()).toBe(
        "&lt;p&gt;test 1&lt;/p&gt;, <p>test 2</p> et &amp;lt;p&amp;gt;test 3&amp;lt;/p&amp;gt;"
    );
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.join keeps html markup and escapes text", () => {
    const res = Markup.join([Markup.build`<p>test</p>`, "<p>test</p>"]);
    expect(res.toString()).toBe("<p>test</p>&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.join escapes text separator", () => {
    const res = Markup.join(["a", "b"], "<br>");
    expect(res.toString()).toBe("a&lt;br&gt;b");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.join keeps html separator", () => {
    const res = Markup.join(["a", "b"], Markup.build`<br>`);
    expect(res.toString()).toBe("a<br>b");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.build`` escapes text in param", () => {
    const res = Markup.build`<div>${"<p>test</p>"}</div>`;
    expect(res.toString()).toBe("<div>&lt;p&gt;test&lt;/p&gt;</div>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.build`` keeps html markup in param", () => {
    const res = Markup.build`<div>${Markup.build`<p>test</p>`}</div>`;
    expect(res.toString()).toBe("<div><p>test</p></div>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.build`` doesn't change text in template", () => {
    const res = Markup.build`&lt;p&gt;test&lt;/p&gt;`;
    expect(res.toString()).toBe("&lt;p&gt;test&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.sprintf escapes str with list params", () => {
    const res = Markup.sprintf("<p>%s</p>", "Hi");
    expect(res.toString()).toBe("&lt;p&gt;Hi&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.sprintf escapes list params", () => {
    const res = Markup.sprintf(
        Markup.build`<p>%s</p>%s`,
        Markup.build`<span>test 1</span>`,
        `<span>test 2</span>`
    );
    expect(res.toString()).toBe(
        "<p><span>test 1</span>,&lt;span&gt;test 2&lt;/span&gt;</p>undefined"
    );
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.sprintf escapes str with object params", () => {
    const res = Markup.sprintf("<p>%(t1)s</p>", { t1: "Hi" });
    expect(res.toString()).toBe("&lt;p&gt;Hi&lt;/p&gt;");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.sprintf escapes object param", () => {
    const res = Markup.sprintf(Markup.build`<p>%(t1)s</p>%(t2)s`, {
        t1: `<span>test 1</span>`,
        t2: Markup.build`<span>test 2</span>`,
    });
    expect(res.toString()).toBe("<p>&lt;span&gt;test 1&lt;/span&gt;</p><span>test 2</span>");
    expect(res).toBeInstanceOf(Markup);
});

test("Markup.isEmpty does not consider text as empty", () => {
    expect(Markup.isEmpty("<p></p>")).toBe(false);
});

test("Markup.isEmpty considers empty html markup as empty", () => {
    expect(Markup.isEmpty(Markup.build`<p></p>`)).toBe(true);
});

test("Markup.setElementContent escapes text", () => {
    const div = document.createElement("div");
    Markup.setElementContent(div, "<p>test</p>");
    expect(div.innerHTML).toBe("&lt;p&gt;test&lt;/p&gt;");
});

test("Markup.setElementContent keeps html markup", () => {
    const div = document.createElement("div");
    Markup.setElementContent(div, Markup.build`<p>test</p>`);
    expect(div.innerHTML).toBe("<p>test</p>");
});
