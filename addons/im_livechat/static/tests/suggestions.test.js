import { describe, test } from "@odoo/hoot";
import {
    click,
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

test("Suggestions are shown after delimiter was used in text (::)", async () => {
    const pyEnv = await startServer();
    pyEnv["mail.canned.response"].create({
        source: "hello",
        substitution: "Hello dear customer, how may I help you?",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                partner_id: serverState.publicPartnerId,
                livechat_member_type: "visitor",
            }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "::");
    await contains(".o-mail-Composer-suggestion strong", { text: "hello" });
    await insertText(".o-mail-Composer-input", ")");
    await contains(".o-mail-Composer-suggestion strong", { count: 0 });
    await insertText(".o-mail-Composer-input", " ::");
    await contains(".o-mail-Composer-suggestion strong", { text: "hello" });
});

test("Cannot mention other channels in a livechat", async () => {
    const pyEnv = await startServer();
    const [channelId] = pyEnv["discuss.channel"].create([
        {
            channel_type: "livechat",
            channel_member_ids: [
                Command.create({
                    partner_id: serverState.partnerId,
                    livechat_member_type: "agent",
                }),
                Command.create({
                    partner_id: serverState.publicPartnerId,
                    livechat_member_type: "visitor",
                }),
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

test("Internal user mention shows their live chat username", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].write([serverState.partnerId], { user_livechat_username: "Batman" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "livechat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({
                partner_id: serverState.publicPartnerId,
                livechat_member_type: "visitor",
            }),
        ],
    });
    pyEnv["res.users"]._applyComputesAndValidate();
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "@");
    await click('.o-mail-Composer-suggestion:contains(Mitchell Admin "Batman")');
    await contains(".o-mail-Composer-input:value(@Batman)");
    await click(".o-mail-Composer button[title='Send']:enabled");
    await contains(".o-mail-Message a.o_mail_redirect", { text: "@Batman" });
});
