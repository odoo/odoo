/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { assertSteps, click, contains, insertText, step } from "@web/../tests/utils";
import { patchWebsocketWorkerWithCleanup } from "@bus/../tests/helpers/mock_websocket";
import { patchDate } from "@web/../tests/helpers/utils";

QUnit.module("discuss");

QUnit.test("Member list and settings menu are exclusive", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await click("[title='Show Member List']");
    await contains(".o-discuss-ChannelMemberList");
    await click("[title='Show Call Settings']");
    await contains(".o-discuss-CallSettings");
    await contains(".o-discuss-ChannelMemberList", { count: 0 });
});

QUnit.test("bus subscription is refreshed when channel is joined", async () => {
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
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { env, openDiscuss } = await start();
    const expectedSubscribes = [];
    for (const { type, id } of env.services["mail.store"].imStatusTrackedPersonas) {
        const model = type === "partner" ? "res.partner" : "mail.guest";
        expectedSubscribes.unshift(`"odoo-presence-${model}_${id}"`);
    }
    await openDiscuss();
    await assertSteps([`subscribe - [${expectedSubscribes.join(",")}]`]);
    await click(".o-mail-DiscussSidebar i[title='Add or join a channel']");
    await insertText(".o-discuss-ChannelSelector input", "new channel");
    await click(".o-discuss-ChannelSelector-suggestion");
    const [newChannel] = pyEnv["discuss.channel"].searchRead([["name", "=", "new channel"]]);
    expectedSubscribes.unshift(`"discuss.channel_${newChannel.id}"`);
    await assertSteps([
        `subscribe - [${expectedSubscribes.join(",")}]`,
        `subscribe - [${expectedSubscribes.join(",")}]`, // 1 is enough. The 2 comes from technical details (1: from channel_join, 2: from channel open), 2nd covers shadowing
    ]);
});

QUnit.test("bus subscription is refreshed when channel is left", async () => {
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
    patchDate(later.year, later.month, later.day, later.hour, later.minute, later.second);
    const { env, openDiscuss } = await start();
    const imStatusChannels = [];
    for (const { type, id } of env.services["mail.store"].imStatusTrackedPersonas) {
        const model = type === "partner" ? "res.partner" : "mail.guest";
        imStatusChannels.unshift(`"odoo-presence-${model}_${id}"`);
    }
    await assertSteps([`subscribe - [${imStatusChannels.join(",")}]`]);
    await openDiscuss();
    await assertSteps([]);
    await click("[title='Leave this channel']");
    await assertSteps([`subscribe - [${imStatusChannels.join(",")}]`]);
});
