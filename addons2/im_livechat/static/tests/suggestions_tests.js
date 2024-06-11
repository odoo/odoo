/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { contains, insertText } from "@web/../tests/utils";

QUnit.module("suggestion");

QUnit.test("Suggestions are shown after delimiter was used in text (:)", async () => {
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
    await contains(".o-mail-Composer-suggestion strong", { text: "hello" });
    await insertText(".o-mail-Composer-input", ")");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " :");
    await contains(".o-mail-Composer-suggestion strong", { text: "hello" });
});

QUnit.test("Cannot mention other channels in a livechat", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor",
            channel_type: "livechat",
            channel_member_ids: [
                Command.create({ partner_id: pyEnv.currentPartnerId }),
                Command.create({ partner_id: pyEnv.publicPartnerId }),
            ],
        },
        {
            channel_type: "channel",
            group_public_id: false,
            name: "Link and Zelda",
        },
    ]);
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestion", { count: 0 });
});
