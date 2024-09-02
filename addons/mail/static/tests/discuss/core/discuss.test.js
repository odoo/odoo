import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/mock_websocket";
import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineMailModels();

test("Member list and Pinned Messages Panel menu are exclusive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click("[title='Members']");
    await contains(".o-discuss-ChannelMemberList");
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
                step(`subscribe - ${JSON.stringify(data.channels)}`);
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    const env = await start();
    const imStatusChannels = [];
    for (const { type, id } of env.services["mail.store"].imStatusTrackedPersonas) {
        const model = type === "partner" ? "res.partner" : "mail.guest";
        imStatusChannels.unshift(`"odoo-presence-${model}_${id}"`);
    }
    await assertSteps([`subscribe - [${imStatusChannels.join(",")}]`]);
    await openDiscuss();
    await assertSteps([]);
    await click(".o-mail-DiscussSidebar [title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "new channel");
    await click(".o-discuss-ChannelSelector-suggestion");
    await assertSteps([`subscribe - [${imStatusChannels.join(",")}]`]);
});

test("bus subscription is refreshed when channel is left", async () => {
    const pyEnv = await startServer();
    pyEnv["discuss.channel"].create({ name: "General" });
    patchWebsocketWorkerWithCleanup({
        _sendToServer({ event_name, data }) {
            if (event_name === "subscribe") {
                step(`subscribe - ${JSON.stringify(data.channels)}`);
            }
        },
    });
    const later = luxon.DateTime.now().plus({ seconds: 2 });
    mockDate(
        `${later.year}-${later.month}-${later.day} ${later.hour}:${later.minute}:${later.second}`
    );
    const env = await start();
    const imStatusChannels = [];
    for (const { type, id } of env.services["mail.store"].imStatusTrackedPersonas) {
        const model = type === "partner" ? "res.partner" : "mail.guest";
        imStatusChannels.unshift(`"odoo-presence-${model}_${id}"`);
    }
    await assertSteps([`subscribe - [${imStatusChannels.join(",")}]`]);
    await openDiscuss();
    await assertSteps([]);
    await click("[title='Leave Channel']");
    await assertSteps([`subscribe - [${imStatusChannels.join(",")}]`]);
});
