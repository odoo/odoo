import {
    defineMailModels,
    listenStoreFetch,
    patchUiSize,
    setupChatHub,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("chat window does not fetch messages if hidden", async () => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([{}, {}, {}]);
    pyEnv["mail.message"].create([
        {
            body: "Orange",
            res_id: channeId1,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Apple",
            res_id: channelId2,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Banana",
            res_id: channelId3,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    patchUiSize({ width: 900 }); // enough for 2 open chat windows max
    listenStoreFetch("/discuss/channel/messages");
    setupChatHub({ opened: [channelId3, channelId2, channeId1] });
    await start();
    await waitFor(".o-mail-ChatWindow:count(2)");
    await waitFor(".o-mail-ChatBubble:count(1)");
    await waitFor(".o-mail-Message-content:text('Banana'):count(1)");
    await waitFor(".o-mail-Message-content:text('Apple'):count(1)");
    await waitForNone(".o-mail-Message-content:contains('Orange')");
    await waitStoreFetch(["/discuss/channel/messages", "/discuss/channel/messages"]);
});

test("click on hidden chat window should fetch its messages", async () => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([{}, {}, {}]);
    pyEnv["mail.message"].create([
        {
            body: "Orange",
            res_id: channeId1,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Apple",
            res_id: channelId2,
            message_type: "comment",
            model: "discuss.channel",
        },
        {
            body: "Banana",
            res_id: channelId3,
            message_type: "comment",
            model: "discuss.channel",
        },
    ]);
    patchUiSize({ width: 900 }); // enough for 2 open chat windows max
    setupChatHub({ opened: [channelId3, channelId2, channeId1] });
    listenStoreFetch("/discuss/channel/messages");
    await start();
    await waitFor(".o-mail-ChatWindow:count(2)");
    await waitFor(".o-mail-ChatBubble:count(1)");
    await waitFor(".o-mail-Message-content:text('Banana'):count(1)");
    await waitFor(".o-mail-Message-content:text('Apple'):count(1)");
    await waitForNone(".o-mail-Message-content:contains('Orange')");
    await waitStoreFetch(["/discuss/channel/messages", "/discuss/channel/messages"]);
    await contains(".o-mail-ChatBubble:count(1)").click();
    await waitFor(".o-mail-Message-content:text('Orange'):count(1)");
    await waitFor(".o-mail-Message-content:text('Banana'):count(1)");
    await waitForNone(".o-mail-Message-content:contains('Apple')");
    await waitStoreFetch(["/discuss/channel/messages"]);
});
