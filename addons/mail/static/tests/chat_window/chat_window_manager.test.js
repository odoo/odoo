import {
    assertSteps,
    click,
    contains,
    defineMailModels,
    onRpcBefore,
    patchUiSize,
    start,
    startServer,
    step,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("chat window does not fetch messages if hidden", async () => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            ],
        },
    ]);
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
    onRpcBefore("/discuss/channel/messages", () => step("fetch_messages"));
    await start();
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatBubble", { count: 1 });
    // FIXME: expected ordering: Banana, Apple, Orange
    await contains(".o-mail-Message-content", { text: "Banana" });
    await contains(".o-mail-Message-content", { text: "Apple" });
    await contains(".o-mail-Message-content", { count: 0, text: "Orange" });
    await assertSteps(["fetch_messages", "fetch_messages"]);
});

test("click on hidden chat window should fetch its messages", async () => {
    const pyEnv = await startServer();
    const [channeId1, channelId2, channelId3] = pyEnv["discuss.channel"].create([
        {
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            ],
        },
        {
            channel_member_ids: [
                Command.create({ fold_state: "open", partner_id: serverState.partnerId }),
            ],
        },
    ]);
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
    onRpcBefore("/discuss/channel/messages", () => step("fetch_messages"));
    await start();
    await contains(".o-mail-ChatWindow", { count: 2 });
    await contains(".o-mail-ChatBubble", { count: 1 });
    // FIXME: expected ordering: Banana, Apple, Orange
    await contains(".o-mail-Message-content", { text: "Banana" });
    await contains(".o-mail-Message-content", { text: "Apple" });
    await contains(".o-mail-Message-content", { count: 0, text: "Orange" });
    await assertSteps(["fetch_messages", "fetch_messages"]);
    await click(".o-mail-ChatBubble");
    await contains(".o-mail-Message-content", { text: "Orange" });
    await contains(".o-mail-Message-content", { text: "Banana" });
    await contains(".o-mail-Message", { count: 0, text: "Apple" });
    await assertSteps(["fetch_messages"]);
});
