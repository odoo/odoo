import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { press } from "@odoo/hoot-dom";

defineMailModels();
describe.current.tags("desktop");

test("Group name is based on channel members when name is not set", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].create(
        ["Alice", "Bob", "Eve", "John", "Sam"].map((name) => ({
            name,
            partner_id: pyEnv["res.partner"].create({ name }),
        }))
    );
    const channelId = pyEnv["discuss.channel"].create({ channel_type: "group" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-threadName[title='Mitchell Admin']");
    await click("button[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Alice" });
    await click("button", { text: "Invite to Group Chat" });
    await contains(".o-mail-DiscussContent-threadName[title='Mitchell Admin and Alice']");
    await click("button[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Bob" });
    await click("button", { text: "Invite to Group Chat" });
    await contains(".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, and Bob']");
    await click("button[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Eve" });
    await click("button", { text: "Invite to Group Chat" });
    await contains(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, Bob, and 1 other']"
    );
    await click("button[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "John" });
    await click("button", { text: "Invite to Group Chat" });
    await contains(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, Bob, and 2 others']"
    );
    await click(".o-mail-DiscussContent-threadName");
    await insertText(".o-mail-DiscussContent-threadName.o-focused", "Custom name", {
        replace: true,
    });
    await contains(".o-mail-DiscussContent-threadName[title='Custom name']");
    await press("Enter");
    // Ensure that after setting the name, members are not taken into account for the group name.
    await click("button[title='Invite People']");
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Sam" });
    await click("button", { text: "Invite to Group Chat" });
    await contains(".o_mail_notification", { text: "invited Sam to the channel" });
    await contains(".o-mail-DiscussContent-threadName[title='Custom name']");
});
