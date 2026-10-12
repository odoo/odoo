import {
    click,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor } from "@odoo/hoot";

import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Start Call in a channel stays inline (not fullscreen)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await waitFor(".o-mail-Discuss .o-discuss-Call:count(1)");
});

test("Start Video Call in a channel opens the fullscreen meeting view", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Video Call']");
    await waitFor(".o-mail-Meeting .o-discuss-Call:count(1)");
});

test("channel video conference exposes Members as a side action", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Video Call']");
    await waitFor(".o-mail-MeetingSideActions button[title='Members']:count(1)");
    await waitFor(".o-mail-MeetingSideActions button[title='Chat']:count(1)");
});

test("Start Call in a group chat stays inline (not fullscreen)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "group",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await waitFor(".o-mail-Discuss .o-discuss-Call:count(1)");
});

test("Start Call in a chat stays inline (not fullscreen)", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "chat",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await waitFor(".o-mail-Discuss .o-discuss-Call:count(1)");
});

test("Start Video Call in a group chat opens the fullscreen meeting view", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Marc" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "group",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
    });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Video Call']");
    await waitFor(".o-mail-Meeting .o-discuss-Call:count(1)");
});
