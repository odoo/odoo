import {
    click,
    contains,
    defineMailModels,
    hover,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("forward message to another channel", async () => {
    const pyEnv = await startServer();
    const [sourceChannelId, targetChannelId] = pyEnv["discuss.channel"].create([
        {
            name: "Source",
            channel_type: "channel",
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        },
        {
            name: "Target",
            channel_type: "channel",
            channel_member_ids: [Command.create({ partner_id: serverState.partnerId })],
        },
    ]);
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "<p>Hello world</p>",
        message_type: "comment",
        model: "discuss.channel",
        res_id: sourceChannelId,
    });
    await start();
    await openDiscuss(sourceChannelId);
    await contains(".o-mail-Message:contains(Hello world)");
    await hover(".o-mail-Message");
    await click(".o-mail-Message-actions button[title='Expand']");
    await click(".o-dropdown-item:text(Forward)");
    await contains(".modal-title:text('Forward To')");
    await click(".o-mail-ForwardDialog-destinations :text(Target)");
    await insertText(".o-mail-ForwardDialog textarea", "My optional note");
    await click(".modal-footer button:text(Send)");
    await openDiscuss(targetChannelId);
    await contains(".o-mail-ForwardedMessage-label:contains(Forwarded)");
    await contains(".o-mail-Message-body:contains(Hello world)");
    await contains(".o-mail-Message:contains(My optional note)");
});
