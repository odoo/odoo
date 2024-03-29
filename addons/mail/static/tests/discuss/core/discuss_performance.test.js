import { describe, test } from "@odoo/hoot";
import {
    assertSteps,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
    step,
    triggerHotkey,
} from "../../mail_test_helpers";
import { onWillRender } from "@odoo/owl";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Message } from "@mail/core/common/message";

describe.current.tags("desktop");
defineMailModels();

test("posting new message should only render relevant part", async () => {
    // For example, it should not render old messages again
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = [];
    for (let i = 0; i < 10; i++) {
        messageIds.push(
            pyEnv["mail.message"].create({
                body: "not empty",
                model: "discuss.channel",
                res_id: channelId,
            })
        );
    }
    messageIds.pop(); // remove last as it might need re-render (it was the newest message before)
    let messagePosted = false;
    patchWithCleanup(Message.prototype, {
        setup() {
            onWillRender(() => {
                if (messagePosted) {
                    if (messageIds.includes(this.message.id)) {
                        throw new Error(
                            "Should not re-render old messages again on posting a new message"
                        );
                    }
                } else {
                    if (messageIds.includes(this.message.id)) {
                        step(`${this.message.id}`);
                    }
                }
            });
            return super.setup();
        },
    });
    await start();
    await openDiscuss(channelId);
    await assertSteps(messageIds.map((id) => `${id}`)); // all messages rendered
    await contains(".o-mail-Message", { count: 10 });
    await insertText(".o-mail-Composer-input", "Test");
    messagePosted = true;
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 11 });
});
