import { expect, test } from "@odoo/hoot";

import { formatText } from "@mail/js/emojis_mixin";

test("Emoji formatter handles compound emojis", () => {
    const testString = "👩🏿test👨‍🚒👩t👩 - 🇧🇪👩\n<test-escape>";
    const expectedString =
        "<span class='o_mail_emoji'>👩🏿</span>test<span class='o_mail_emoji'>👨‍🚒</span><span class='o_mail_emoji'>👩</span>t<span class='o_mail_emoji'>👩</span> - <span class='o_mail_emoji'>🇧🇪</span><span class='o_mail_emoji'>👩</span><br>&lt;test-escape&gt;";
    expect(formatText(testString).toString()).toBe(expectedString);
});
