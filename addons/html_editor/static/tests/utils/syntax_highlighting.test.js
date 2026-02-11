import { getPreValue } from "@html_editor/others/embedded_components/core/syntax_highlighting/syntax_highlighting_utils";
import { describe, expect, test } from "@odoo/hoot";
import { insertTestHtml } from "../_helpers/editor";

describe("getPreValue", () => {
    test("preserves multiple consecutive br as multiple newlines", () => {
        const [pre] = insertTestHtml("<pre>abc<br><br>def</pre>");
        expect(getPreValue(pre)).toBe("abc\n\ndef");
    });

    test("converts br to newlines and removes only trailing br", () => {
        const [pre] = insertTestHtml("<pre>abc<br>def<br><br></pre>");
        expect(getPreValue(pre)).toBe("abc\ndef\n");
    });

    test("returns empty string for empty pre (single br)", () => {
        const [pre] = insertTestHtml("<pre><br></pre>");
        expect(getPreValue(pre)).toBe("");
    });

    test("strips html tags and decodes all entities", () => {
        const [pre] = insertTestHtml(
            "<pre><span>&lt;div&gt;</span><br><strong>&amp;</strong><br>&#x27;quote&#x27;<br>&quot;double&quot;<br>&#x60;backtick&#x60;</pre>"
        );
        expect(getPreValue(pre)).toBe("<div>\n&\n'quote'\n\"double\"\n`backtick`");
    });

    test("removes zero-width characters", () => {
        const [pre] = insertTestHtml("<pre>a\u200Bb\uFEFFc</pre>");
        expect(getPreValue(pre)).toBe("abc");
    });

    test("converts br to newlines even when pre has display none", () => {
        const [container] = insertTestHtml(
            '<div style="display:none"><pre>hidden<br>content<br><br><br></pre></div>'
        );
        const pre = container.querySelector("pre");
        expect(getPreValue(pre)).toBe("hidden\ncontent\n\n");
    });
});
