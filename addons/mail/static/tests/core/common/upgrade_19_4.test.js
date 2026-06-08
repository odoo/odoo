import { describe, expect, test } from "@odoo/hoot";
import {
    contains,
    defineMailModels,
    setupChatHub,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { ChatHub } from "@mail/core/common/chat_hub_model";

describe.current.tags("desktop");
defineMailModels();

test("chathub compact is 'on'", async () => {
    const pyEnv = await startServer();
    const channelIds = [];
    for (let i = 1; i <= 20; i++) {
        channelIds.push(pyEnv["discuss.channel"].create({ name: String(i) }));
    }
    setupChatHub({ folded: channelIds.reverse() });
    localStorage.setItem("mail.user_setting.chathub_compact", "true");
    await start();
    await contains(".o-mail-ChatBubble", { count: 1 });
    await contains(".o-mail-ChatBubble i.fa.fa-comments");
    const isChathubCompact = makeRecordFieldLocalId(ChatHub.localId(), "compact");
    expect(localStorage.getItem(isChathubCompact)).toBe(toRawValue(true));
    expect(localStorage.getItem("mail.user_setting.chathub_compact")).toBe(null);
});
