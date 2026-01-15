import { expect, test } from "@odoo/hoot";

import { formatText } from "@mail/js/emojis_mixin";

test("Emoji formatter handles compound emojis", () => {
    const testString = "<p>👩🏿test👩🏿👩t👩</p>";
    const expectedString =
        "&lt;p&gt;<span class='o_mail_emoji'>👩🏿</span>test<span class='o_mail_emoji'>👩🏿👩</span>t<span class='o_mail_emoji'>👩</span>&lt;/p&gt;";
    expect(formatText(testString).toString()).toBe(expectedString);
});
