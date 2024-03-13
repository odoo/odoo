import { Command } from "@web/../tests/web_test_helpers";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "../../../mail_test_helpers";
import { waitForChannels, waitUntilSubscribe } from "@bus/../tests/bus_test_helpers";
import { tick } from "@odoo/hoot-mock";
import { withUser } from "@web/../tests/_framework/mock_server/mock_server";
import { describe, test } from "@odoo/hoot";
import { rpcWithEnv } from "@mail/utils/common/misc";

describe.current.tags("desktop");
defineMailModels();

/** @type {ReturnType<import("@mail/utils/common/misc").rpcWithEnv>} */
let rpc;

test("bus subscription updated when joining/leaving thread as non member", async () => {
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
        name: "General",
    });
    await start();
    await Promise.all([openDiscuss(channelId), waitForChannels([`discuss.channel_${channelId}`])]);
    await click("[title='Leave this channel']");
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test("bus subscription updated when joining locally pinned thread", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [],
        name: "General",
    });
    await start();
    await Promise.all([openDiscuss(channelId), waitForChannels([`discuss.channel_${channelId}`])]);
    await click("[title='Add Users']");
    await click(".o-discuss-ChannelInvitation-selectable", {
        text: "Mitchell Admin",
    });
    await click("button", { text: "Invite to Channel" });
    await waitForChannels([`discuss.channel_${channelId}`], { operation: "delete" });
});

test.skip("bus subscription kept after receiving a message as non member", async () => {
    const pyEnv = await startServer();
    const johnUser = pyEnv["res.users"].create({ name: "John" });
    const johnPartner = pyEnv["res.partner"].create({ name: "John", user_ids: [johnUser] });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [Command.create({ partner_id: johnPartner })],
        name: "General",
    });
    const env = await start();
    rpc = rpcWithEnv(env);
    await Promise.all([openDiscuss(channelId), waitUntilSubscribe(`discuss.channel_${channelId}`)]);
    await withUser(johnUser, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Hello!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "Hello!" });
    await tick();
    await withUser(johnUser, () =>
        rpc("/mail/message/post", {
            post_data: { body: "Goodbye!", message_type: "comment" },
            thread_id: channelId,
            thread_model: "discuss.channel",
        })
    );
    await contains(".o-mail-Message", { text: "Goodbye!" });
});
