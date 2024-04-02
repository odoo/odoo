import { describe, expect, test } from "@odoo/hoot";
import {
    assertSteps,
    contains,
    defineMailModels,
    insertText,
    observeRenders,
    openDiscuss,
    prepareObserveRenders,
    start,
    startServer,
    step,
    triggerHotkey,
} from "../../mail_test_helpers";
import { onWillRender } from "@odoo/owl";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { Message } from "@mail/core/common/message";
import { Composer } from "@mail/core/common/composer";

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
    let posting = false;
    prepareObserveRenders();
    patchWithCleanup(Message.prototype, {
        setup() {
            onWillRender(() => {
                if (posting) {
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
    const stopObserve = observeRenders();
    posting = true;
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 11 });
    posting = false;
    const result = stopObserve();
    // LessThan because renders could be batched
    expect(result.get(Composer)).toBeLessThan(3); // 2: temp disabling + clear content
    expect(result.get(Message)).toBeLessThan(4); // 3|2: (new temp msg) + new genuine msg + prev msg -- new temp msg usually batched destroyed
});
