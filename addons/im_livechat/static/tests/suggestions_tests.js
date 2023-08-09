/* @odoo-module */

import { Command } from "@mail/../tests/helpers/command";
import { insertText, start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("suggestion");

QUnit.test("Suggestions are shown after delimiter was used in text (:)", async (assert) => {
    const pyEnv = await startServer();
    pyEnv["mail.shortcode"].create({
        source: "hello",
        substitution: "Hello dear customer, how may I help you?",
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: pyEnv.currentPartnerId }),
            Command.create({ partner_id: pyEnv.publicPartnerId }),
        ],
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":");
    assert.containsOnce($, ".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", ")");
    assert.containsNone($, ".o-mail-Composer-suggestion");
    await insertText(".o-mail-Composer-input", " ");
    await insertText(".o-mail-Composer-input", ":");
    assert.containsOnce($, ".o-mail-Composer-suggestion:contains(hello)");
});
