import {
    click,
    contains,
    defineMailModels,
    insertText,
    observeRenders,
    openDiscuss,
    prepareObserveRenders,
    scroll,
    start,
    startServer,
    triggerHotkey,
} from "@mail/../tests/mail_test_helpers";
import { Composer } from "@mail/core/common/composer";
import { Message } from "@mail/core/common/message";
import { describe, expect, queryAll, rightClick, test, tick } from "@odoo/hoot";
import { onMounted, onPatched } from "@odoo/owl";
import { Command, patchWithCleanup, serverState, withUser } from "@web/../tests/web_test_helpers";
import { rpc } from "@web/core/network/rpc";
import { range } from "@web/core/utils/numbers";

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

test("replying to message should only render relevant part", async () => {
    // For example, it should not render all messages when selecting message to reply
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = pyEnv["mail.message"].create(
        range(10).map((i) => ({ body: `${i}`, model: "discuss.channel", res_id: channelId }))
    );
    messageIds.pop(); // remove last as this is the one to be replied to
    let replying = false;
    prepareObserveRenders();
    patchWithCleanup(Message.prototype, {
        setup() {
            const cb = () => {
                if (replying) {
                    if (messageIds.includes(this.message.id)) {
                        throw new Error(
                            "Should not re-render other messages on replying to a message"
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
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 10 });
    const stopObserve = observeRenders();
    replying = true;
    await click(".o-mail-Message:last [title='Reply']");
    await contains(".o-mail-Composer:has(:text('Replying to Mitchell Admin'))");
    replying = false;
    const result = stopObserve();
    expect(result.get(Composer)).toBeLessThan(2);
    expect(result.get(Message)).toBeLessThan(2);
});

test("right-click message selection should only render relevant part", async () => {
    // For example, it should not render all messages when right-click selecting message from opening dropdown with actions
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = pyEnv["mail.message"].create(
        range(10).map((i) => ({ body: `${i}`, model: "discuss.channel", res_id: channelId }))
    );
    messageIds.pop(); // remove last as this is the one to be right-clicking
    let rightClicking = false;
    prepareObserveRenders();
    patchWithCleanup(Message.prototype, {
        setup() {
            const cb = () => {
                if (rightClicking) {
                    if (messageIds.includes(this.message.id)) {
                        throw new Error(
                            "Should not re-render other messages on right-clicking on a message"
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
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 10 });
    const stopObserve = observeRenders();
    rightClicking = true;
    await rightClick(".o-mail-Message:last");
    await contains(".dropdown-menu .o-mail-ActionList");
    rightClicking = false;
    const result = stopObserve();
    expect(result.get(Message)).toBeLessThan(2);
});

test("load older auto-unload messages in message list", async () => {
    // So that message list has a max amount of messages in DOM, to ensure there's a ceiling to performance hit when re-rendering whole message list
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const messageIds = range(0, 1000).map((i) =>
        pyEnv["mail.message"].create({ body: `${i}`, model: "discuss.channel", res_id: channelId })
    );
    const newestMessageId = messageIds.at(-1);
    const [selfMember] = pyEnv["discuss.channel.member"].search_read([
        ["partner_id", "=", serverState.partnerId],
        ["channel_id", "=", channelId],
    ]);
    pyEnv["discuss.channel.member"].write([selfMember.id], {
        new_message_separator: newestMessageId + 1,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await contains(`.o-mail-Message:has(:text('970'))`);
    await contains("button", { text: "Load More", before: [".o-mail-Message", { count: 30 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(970, 1000)
            .map((n) => `${n}`)
            .join(",")
    );
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message:has(:text('940'))");
    await contains("button", { text: "Load More", before: [".o-mail-Message", { count: 60 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(940, 1000)
            .map((n) => `${n}`)
            .join(",")
    );
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message:has(:text('910'))");
    await contains("button", { text: "Load More", before: [".o-mail-Message", { count: 90 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(910, 1000)
            .map((n) => `${n}`)
            .join(",")
    );
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", 0);
    await contains(".o-mail-Message:has(:text('880'))");
    await contains("button", { text: "Load More", before: [".o-mail-Message", { count: 90 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(880, 970)
            .map((n) => `${n}`)
            .join(",")
    );
});

test("load newer auto-unload messages in message list", async () => {
    // So that message list has a max amount of messages in DOM, to ensure there's a ceiling to performance hit when re-rendering whole message list
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    range(0, 1000).map((i) =>
        pyEnv["mail.message"].create({ body: `${i}`, model: "discuss.channel", res_id: channelId })
    );
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message", { count: 30 });
    await contains(".o-mail-Thread", { scroll: 0 });
    await contains(".o-mail-Message:has(:text('0'))");
    await contains("button", { text: "Load More", after: [".o-mail-Message", { count: 30 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(0, 30)
            .map((n) => `${n}`)
            .join(",")
    );
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Message:has(:text('30'))");
    await contains("button", { text: "Load More", after: [".o-mail-Message", { count: 60 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(0, 60)
            .map((n) => `${n}`)
            .join(",")
    );
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Message:has(:text('60'))");
    await contains("button", { text: "Load More", after: [".o-mail-Message", { count: 90 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(0, 90)
            .map((n) => `${n}`)
            .join(",")
    );
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Message:has(:text('90'))");
    await contains("button", { text: "Load More", after: [".o-mail-Message", { count: 90 }] });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(30, 120)
            .map((n) => `${n}`)
            .join(",")
    );
});

test("on new messages auto-unload messages in message list", async () => {
    // So that message list has a max amount of messages in DOM, to ensure there's a ceiling to performance hit when re-rendering whole message list
    const pyEnv = await startServer();
    const bobPartnerId = pyEnv["res.partner"].create({ name: "Bob" });
    const bobUserId = pyEnv["res.users"].create({ name: "Bob", partner_id: bobPartnerId });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: bobPartnerId }),
        ],
        channel_type: "chat",
    });
    pyEnv["mail.message"].create(
        range(0, 85).map((i) => ({
            body: `${i}`,
            model: "discuss.channel",
            res_id: channelId,
        }))
    );
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message:has(:text('29'))");
    await contains("button", { text: "Load More", after: [".o-mail-Message", { count: 30 }] });
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Message:has(:text('59'))");
    await contains("button", { text: "Load More", after: [".o-mail-Message", { count: 60 }] });
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Message:has(:text('84'))");
    await contains(".o-mail-Message", { count: 85 });
    await tick(); // wait for scroll adjustment
    await scroll(".o-mail-Thread", "bottom");
    await contains(".o-mail-Thread", { scroll: "bottom" });
    await contains("button", {
        text: "Load More",
        after: [".o-mail-Message", { count: 85 }],
        count: 0,
    });
    for (const i of range(85, 95)) {
        await withUser(bobUserId, () =>
            rpc("/mail/message/post", {
                post_data: {
                    body: `${i}`,
                    message_type: "comment",
                    subtype_xmlid: "mail.mt_comment",
                },
                thread_id: channelId,
                thread_model: "discuss.channel",
            })
        );
    }
    await contains(`.o-mail-Message:has(:text('94'))`);
    await contains(".o-mail-Message", { count: 90 });
    expect(
        queryAll(".o-mail-Message-content")
            .map((node) => node.textContent)
            .join(",")
    ).toBe(
        range(5, 95)
            .map((n) => `${n}`)
            .join(",")
    );
});
