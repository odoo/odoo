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
import { Command, withUser } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("user joins the channel", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "Sales", channel_member_ids: [] });
    await start();
    await openDiscuss();
    await click("[placeholder='Find or start a conversation']");
    await click(".o-mail-DiscussCommand", { text: "Sales" });
    await insertText(".o-mail-Composer-input", "Hello!"); // User is added during `notify_typing`
    await contains(".o-mail-NotificationMessage", { text: "Mitchell Admin joined the channel" });
});

test("user joins and deleted afterwards", async () => {
    const pyEnv = await startServer();
    const salesId = pyEnv["discuss.channel"].create({ name: "Sales", channel_member_ids: [] });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob" });
    const bobId = pyEnv["res.partner"].create({ name: "Bob", user_ids: [bobUserId] });
    await withUser(bobUserId, () => pyEnv["discuss.channel"].add_members([salesId], [bobId]));
    const [bobMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", salesId],
        ["partner_id", "=", bobId],
    ]);
    pyEnv["discuss.channel.member"].unlink(bobMemberId);
    pyEnv["res.partner"].unlink(bobId);
    await start();
    await openDiscuss(salesId);
    await contains(".o-mail-NotificationMessage", {
        text: "Deleted user joined the channel",
    });
});

test("user invited to the channel", async () => {
    const pyEnv = await startServer();
    const salesId = pyEnv["discuss.channel"].create({ name: "Sales" });
    const bobId = pyEnv["res.partner"].create({
        name: "Bob",
        user_ids: [Command.create({ name: "Bob" })],
    });
    await start();
    await openDiscuss(salesId);
    await click("button", { text: "Invite a User" });
    await click(".o-discuss-ChannelInvitation-selectable", { text: "Bob" });
    await click("[title='Invite to Channel']:enabled");
    await contains(`a[data-oe-model='res.partner'][data-oe-id='${bobId}']`, {
        text: "@Bob",
        parent: [
            ".o-mail-NotificationMessage",
            { text: "Mitchell Admin invited @Bob to the channel" },
        ],
    });
});

test("user invited, invitee deleted afterwards", async () => {
    const pyEnv = await startServer();
    const bobId = pyEnv["res.partner"].create({
        name: "Bob",
        user_ids: [Command.create({ name: "Bob" })],
    });
    const salesId = pyEnv["discuss.channel"].create({ name: "Sales" });
    pyEnv["discuss.channel"].add_members([salesId], [bobId]);
    const [bobMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", salesId],
        ["partner_id", "=", bobId],
    ]);
    pyEnv["discuss.channel.member"].unlink(bobMemberId);
    pyEnv["res.partner"].unlink(bobId);
    await start();
    await openDiscuss(salesId);
    await contains(".o-mail-NotificationMessage", {
        text: "Mitchell Admin invited @Deleted user to the channel",
    });
});

test("user invited, inviter deleted afterwards", async () => {
    const pyEnv = await startServer();
    const johnUserId = pyEnv["res.users"].create({ name: "John" });
    const [bobId, johnId] = pyEnv["res.partner"].create([
        {
            name: "Bob",
            user_ids: [Command.create({ name: "Bob" })],
        },
        { name: "John", user_ids: [johnUserId] },
    ]);
    const salesId = pyEnv["discuss.channel"].create({ name: "Sales" });
    await withUser(johnUserId, () => pyEnv["discuss.channel"].add_members([salesId], [bobId]));
    const [johnMemberId] = pyEnv["discuss.channel.member"].search([
        ["channel_id", "=", salesId],
        ["partner_id", "=", johnId],
    ]);
    pyEnv["discuss.channel.member"].unlink(johnMemberId);
    pyEnv["res.partner"].unlink(johnId);
    await start();
    await openDiscuss(salesId);
    await contains(`a[data-oe-model='res.partner'][data-oe-id='${bobId}']`, {
        text: "@Bob",
        parent: [
            ".o-mail-NotificationMessage",
            { text: "Deleted user invited @Bob to the channel" },
        ],
    });
});
