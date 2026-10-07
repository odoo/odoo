import {
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";
import { press, waitFor } from "@odoo/hoot-dom";
import { contains } from "@web/../tests/web_test_helpers";

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
    await contains("button[title='Add People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('Alice')):count(1)").click();
    await contains("button:text('Invite to Group Chat'):count(1)").click();
    await waitFor(".o-mail-DiscussContent-threadName[title='Mitchell Admin and Alice']:count(1)");
    await contains("button[title='Add People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('Bob')):count(1)").click();
    await contains("button:text('Invite to Group Chat'):count(1)").click();
    await waitFor(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, and Bob']:count(1)"
    );
    await contains("button[title='Add People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('Eve')):count(1)").click();
    await contains("button:text('Invite to Group Chat'):count(1)").click();
    await waitFor(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, Bob, and 1 other']:count(1)"
    );
    await contains("button[title='Add People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('John')):count(1)").click();
    await contains("button:text('Invite to Group Chat'):count(1)").click();
    await waitFor(
        ".o-mail-DiscussContent-threadName[title='Mitchell Admin, Alice, Bob, and 2 others']:count(1)"
    );
    await contains(".o-mail-DiscussContent-threadName:count(1)").click();
    await insertText(".o-mail-DiscussContent-threadName.o-focused", "Custom name", {
        replace: true,
    });
    await waitFor(".o-mail-DiscussContent-threadName[title='Custom name']:count(1)");
    await press("Enter");
    // Ensure that after setting the name, members are not taken into account for the group name.
    await contains("button[title='Add People']:count(1)").click();
    await contains(".o-discuss-ChannelInvitation-selectable:has(:text('Sam')):count(1)").click();
    await contains("button:text('Invite to Group Chat'):count(1)").click();
    await waitFor(".o_mail_notification:text('invited Sam to the channel'):count(1)");
    await waitFor(".o-mail-DiscussContent-threadName[title='Custom name']:count(1)");
});
