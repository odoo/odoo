import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/mock_websocket";
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
import { mockDate } from "@odoo/hoot-mock";
import { asyncStep, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Member list and Pinned Messages Panel menu are exclusive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-discuss-ChannelMemberList"); // member list open by default
    await click("[title='Pinned Messages']");
    await contains(".o-discuss-PinnedMessagesPanel");
    await contains(".o-discuss-ChannelMemberList", { count: 0 });
});

test("bus subscription is refreshed when channel is joined", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create([{ name: "General" }, { name: "Sales" }]);
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                if (data.channels.some((channel) => channel.includes("discuss.channel"))) {
                    asyncStep("channel");
                }
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await openDiscuss();
    await click("input[placeholder='Find or start a conversation']");
    await insertText("input[placeholder='Search a conversation']", "new channel");
    await waitForSteps([]);
    await click("a", { text: "Create Channel" });
    await contains(".o-mail-DiscussSidebar-item", { text: "new channel" });
    await waitForSteps(["channel"]);
});

test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                if (data.channels.some((channel) => channel.includes("discuss.channel"))) {
                    asyncStep("channel");
                } else {
                    asyncStep("not-channel");
                }
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    await start();
    await openDiscuss();
    await waitForSteps(["not-channel"]);
    // race-condition: a second call might or might not be present
    await waitForSteps(["not-channel"], { required: false });
    await click("[title='Leave Channel']");
    await click("button", { text: "Leave Conversation" });
    await contains(".o-mail-DiscussSidebarChannel", { count: 0 });
    await waitForSteps(["not-channel"]);
});
