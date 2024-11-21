import { describe, test } from "@odoo/hoot";
import {
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Suggestions are shown after delimiter was used in text (:)", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello dear customer, how may I help you?",
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor",
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: serverState.publicPartnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", ":");
    await contains(".o-mail-Composer-suggestion strong", { text: "hello" });
    await insertText(".o-mail-Composer-input", ")");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " :");
    await contains(".o-mail-Composer-suggestion strong", { text: "hello" });
});

test("Cannot mention other channels in a livechat", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        {
            anonymous_name: "Visitor",
            channel_type: "livechat",
            channel_member_ids: [
                Command.create({ partner_id: serverState.partnerId }),
                Command.create({ partner_id: serverState.publicPartnerId }),
            ],
        },
        {
            channel_type: "channel",
            group_public_id: false,
            name: "Link and Zelda",
        },
    ]);
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "#");
    await contains(".o-mail-Composer-suggestion", { count: 0 });
});
