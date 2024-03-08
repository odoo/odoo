/** @odoo-module alias=@mail/../tests/emoji/emojis_mixin_tests default=false */
const test = QUnit.test; // QUnit.test()

import { formatText } from "@mail/js/emojis_mixin";

QUnit.module("emojis mixin");

test("Emoji formatter handles compound emojis", (assert) => {
    const testString = "👩🏿test👩🏿👩t👩";
    const expectedString =
        "<span class='o_mail_emoji'>👩🏿</span>test<span class='o_mail_emoji'>👩🏿👩</span>t<span class='o_mail_emoji'>👩</span>";
    assert.deepEqual(formatText(testString), expectedString);
});
