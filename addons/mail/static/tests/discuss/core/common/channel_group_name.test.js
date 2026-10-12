import {
    click,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { press, waitFor } from "@odoo/hoot-dom";

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
    await waitFor(".o-mail-DiscussContent-threadName[title='Mitchell Admin']:count(1)");
    await click("button[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Alice'))");
    await click("button:text('Invite to Group Chat')");
    await waitFor(".o-mail-DiscussContent-threadName[title='Mitchell Admin and Alice']:count(1)");
    await click("button[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Bob'))");
    await click("button:text('Invite to Group Chat')");
    await waitFor(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, and Bob']:count(1)"
    );
    await click("button[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Eve'))");
    await click("button:text('Invite to Group Chat')");
    await waitFor(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, Bob, and 1 other']:count(1)"
    );
    await click("button[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('John'))");
    await click("button:text('Invite to Group Chat')");
    await waitFor(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, Bob, and 2 others']:count(1)"
    );
    await click(".o-mail-DiscussContent-threadName");
    await insertText(".o-mail-DiscussContent-threadName.o-focused", "Custom name", {
        replace: true,
    });
    await waitFor(".o-mail-DiscussContent-threadName[title='Custom name']:count(1)");
    await press("Enter");
    // Ensure that after setting the name, members are not taken into account for the group name.
    await click("button[title='Add People']");
    await click(".o-discuss-ChannelInvitation-selectable:has(:text('Sam'))");
    await click("button:text('Invite to Group Chat')");
    await waitFor(".o_mail_notification:text('invited Sam to the channel'):count(1)");
    await waitFor(".o-mail-DiscussContent-threadName[title='Custom name']:count(1)");
});
