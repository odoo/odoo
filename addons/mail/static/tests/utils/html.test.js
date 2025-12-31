import { getInnerHtml, getOuterHtml } from "@mail/utils/common/html";

import { describe, expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";

import { createElementWithContent } from "@web/core/utils/html";

const Markup = markup().constructor;

describe.current.tags("headless");

test("getInnerHtml escapes text and attributes", () => {
    const div = document.createElement("div");
    div.textContent = 'class="test" <i>abc</i>';
    const span = document.createElement("span");
    span.setAttribute("title", "<b>test</b>");
    span.setAttribute("data-test", '" hack="failed');
    div.appendChild(span);
    const res = getInnerHtml(div);
    expect(res.toString()).toBe(
        'class=&quot;test&quot; &lt;i&gt;abc&lt;/i&gt;<span title="&lt;b&gt;test&lt;/b&gt;" data-test="&quot; hack=&quot;failed"></span>'
    );
    // ensure nothing is lost during conversion, the original node can be re-created
    expect(createElementWithContent("dummy", res).innerHTML).toBe(div.innerHTML);
});

test("getOuterHtml escapes text and attributes", () => {
    const div = document.createElement("div");
    div.textContent = 'class="test" <i>abc</i>';
    const span = document.createElement("span");
    span.setAttribute("title", "<b>test</b>");
    span.setAttribute("data-test", '" hack="failed');
    div.appendChild(span);
    const res = getOuterHtml(div);
    expect(res.toString()).toBe(
        '<div>class=&quot;test&quot; &lt;i&gt;abc&lt;/i&gt;<span title="&lt;b&gt;test&lt;/b&gt;" data-test="&quot; hack=&quot;failed"></span></div>'
    );
    // ensure nothing is lost during conversion, the original node can be re-created
    expect(createElementWithContent("dummy", res).innerHTML).toBe(div.outerHTML);
});

test("getInnerHtml ignores text nodes", () => {
    const res = getInnerHtml(document.createTextNode("<span>test</span>"));
    expect(res.toString()).toBe("");
});

test("getOuterHtml escapes text nodes", () => {
    const res = getOuterHtml(document.createTextNode("<span>test</span>"));
    expect(res.toString()).toBe("<span>test</span>");
    expect(res).not.toBeInstanceOf(Markup);
});

test("getOuterHtml ignores comment nodes", () => {
    const res = getOuterHtml(document.createComment("<span>test</span>"));
    expect(res.toString()).toBe("");
});
