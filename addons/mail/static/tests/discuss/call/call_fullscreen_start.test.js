import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Start Call in a channel stays inline (not fullscreen)", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await contains(".o-mail-Discuss .o-discuss-Call");
});

test("Start Video Call in a channel opens the fullscreen meeting view", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Video Call']");
    await contains(".o-mail-Meeting .o-discuss-Call");
});

test("channel video conference exposes Members as a side action", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Video Call']");
    await contains(".o-mail-MeetingSideActions button[title='Members']");
    await contains(".o-mail-MeetingSideActions button[title='Chat']");
});

test("Start Call in a group chat opens the fullscreen meeting view", async () => {
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
    await contains(".o-mail-Meeting .o-discuss-Call");
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
    await contains(".o-mail-Meeting .o-discuss-Call");
});
