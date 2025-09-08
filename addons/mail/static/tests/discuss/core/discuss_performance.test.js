import {
    contains,
    defineMailModels,
    insertText,
    observeRenders,
    openDiscuss,
    prepareObserveRenders,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { Composer } from "@mail/core/common/composer";
import { Message } from "@mail/core/common/message";
import { describe, expect, test } from "@odoo/hoot";
import { onMounted, onPatched } from "@odoo/owl";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

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
                body: `not_empty_${i}`,
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
            const cb = () => {
                if (posting) {
                    if (messageIds.includes(this.message.id)) {
                        throw new Error(
                            "Should not re-render old messages again on posting a new message"
                        );
                    }
                }
            };
            onMounted(cb);
            onPatched(cb);
            return super.setup();
        },
    });
    await start();
    const stopObserve1 = observeRenders();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 10 });
    await insertText(".o-mail-Composer-input", "Test");
    const result1 = stopObserve1();
    // LessThan because renders could be batched
    expect(result1.get(Message)).toBeLessThan(11); // 10: all messages initially
    const stopObserve2 = observeRenders();
    posting = true;
    triggerHotkey("Enter");
    await contains(".o-mail-Message", { count: 11 });
    posting = false;
    const result2 = stopObserve2();
    expect(result2.get(Composer)).toBeLessThan(3); // 2: temp disabling + clear content
    expect(result2.get(Message)).toBeLessThan(4); // 3: new temp msg + new genuine msg + prev msg
});
