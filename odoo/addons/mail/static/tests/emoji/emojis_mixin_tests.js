/* @odoo-module */

import { formatText } from "@mail/js/emojis_mixin";

QUnit.module("emojis mixin");

QUnit.test("Emoji formatter handles compound emojis", (assert) => {
    const testString = "👩🏿test👩🏿👩t👩";
    const expectedString =
        "<span class='o_mail_emoji'>👩🏿</span>test<span class='o_mail_emoji'>👩🏿👩</span>t<span class='o_mail_emoji'>👩</span>";
    assert.deepEqual(formatText(testString), expectedString);
});
