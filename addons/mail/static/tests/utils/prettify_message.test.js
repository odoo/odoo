import { expect, test } from "@odoo/hoot";
import { markup } from "@odoo/owl";

import { prettifyMessageContent } from "@mail/utils/common/format";
const Markup = markup().constructor;

test("prettifyMessageContent follows the same behaviour as plaintext2html with with_paragraph", async () => {
    const result = await prettifyMessageContent(
        "this is a test😇<i>false italic</i>\nnew line\n\ndouble line\n\n\ntriple line",
        { withParagraph: true }
    );
    expect(result).toBeInstanceOf(Markup);
    expect(result.toString()).toEqual(
        "<p>this is a test😇&lt;i&gt;false italic&lt;/i&gt;<br>new line</p><p>double line</p><p>triple line</p>"
    );
});

test("prettifyMessageContent keeps up to 2 new lines by default", async () => {
    const result = await prettifyMessageContent(
        "this is a test😇<i>false italic</i>\nnew line\n\ndouble line\n\n\ntriple line"
    );
    expect(result).toBeInstanceOf(Markup);
    expect(result.toString()).toEqual(
        "this is a test😇&lt;i&gt;false italic&lt;/i&gt;<br>new line<br><br>double line<br><br>triple line"
    );
});
