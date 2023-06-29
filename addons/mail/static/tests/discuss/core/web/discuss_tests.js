/* @odoo-module */

import {
    afterNextRender,
    click,
    insertText,
    start,
    startServer,
} from "@mail/../tests/helpers/test_utils";
import { DEBOUNCE_FETCH_SUGGESTION_TIME } from "@mail/core/common/suggestion_service";

import { editInput, nextTick, triggerEvent, triggerHotkey } from "@web/../tests/helpers/utils";

QUnit.module("discuss");

QUnit.test("can create a new channel [REQUIRE FOCUS]", async (assert) => {
    await startServer();
    const { advanceTime, openDiscuss } = await start({
        hasTimeControl: true,
        mockRPC(route, params) {
            if (
                route.startsWith("/mail") ||
                route.startsWith("/discuss") ||
                [
                    "/web/dataset/call_kw/discuss.channel/search_read",
                    "/web/dataset/call_kw/discuss.channel/channel_create",
                ].includes(route)
            ) {
                assert.step(route);
            }
        },
    });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");

    await click(".o-mail-DiscussSidebar i[title='Add or join a channel']");
    await afterNextRender(() =>
        editInput(document.body, ".o-discuss-ChannelSelector input", "abc")
    );
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await click(".o-discuss-ChannelSelector-suggestion");
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Discuss-content .o-mail-Message");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
        "/web/dataset/call_kw/discuss.channel/search_read",
        "/web/dataset/call_kw/discuss.channel/channel_create",
        "/discuss/channel/messages",
    ]);
});

QUnit.test(
    "do not close channel selector when creating chat conversation after selection",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategoryItem");

        await click("i[title='Start a conversation']");
        await afterNextRender(async () => {
            editInput(document.body, ".o-discuss-ChannelSelector input", "mario");
            await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
        });
        await click(".o-discuss-ChannelSelector-suggestion");
        assert.containsOnce($, ".o-discuss-ChannelSelector span[title='Mario']");
        assert.containsNone($, ".o-mail-DiscussCategoryItem");

        await triggerEvent(document.body, ".o-discuss-ChannelSelector input", "keydown", {
            key: "Backspace",
        });
        assert.containsNone($, ".o-discuss-ChannelSelector span[title='Mario']");

        await afterNextRender(async () => {
            editInput(document.body, ".o-discuss-ChannelSelector input", "mario");
            await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
        });
        await triggerEvent(document.body, ".o-discuss-ChannelSelector input", "keydown", {
            key: "Enter",
        });
        assert.containsOnce($, ".o-discuss-ChannelSelector span[title='Mario']");
        assert.containsNone($, ".o-mail-DiscussCategoryItem");
    }
);

QUnit.test("can join a chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Mario" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const { advanceTime, openDiscuss } = await start({
        hasTimeControl: true,
        mockRPC(route, params) {
            if (
                route.startsWith("/mail") ||
                route.startsWith("/discuss") ||
                ["/web/dataset/call_kw/discuss.channel/channel_get"].includes(route)
            ) {
                assert.step(route);
            }
            if (route === "/web/dataset/call_kw/discuss.channel/channel_get") {
                assert.equal(params.kwargs.partners_to[0], partnerId);
            }
        },
    });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");

    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await afterNextRender(() =>
        editInput(document.body, ".o-discuss-ChannelSelector input", "mario")
    );
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await click(".o-discuss-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-discuss-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsOnce($, ".o-mail-DiscussCategoryItem");
    assert.containsNone($, ".o-mail-Message");
    assert.verifySteps([
        "/mail/init_messaging",
        "/mail/load_message_failures",
        "/mail/inbox/messages",
        "/web/dataset/call_kw/discuss.channel/channel_get",
        "/discuss/channel/messages",
    ]);
});

QUnit.test("can create a group chat conversation", async (assert) => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2] = pyEnv["res.partner"].create([
        { name: "Mario" },
        { name: "Luigi" },
    ]);
    pyEnv["res.users"].create([{ partner_id: partnerId_1 }, { partner_id: partnerId_2 }]);
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss();
    assert.containsNone($, ".o-mail-DiscussCategoryItem");
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await insertText(".o-discuss-ChannelSelector input", "Mario");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await click(".o-discuss-ChannelSelector-suggestion");
    await insertText(".o-discuss-ChannelSelector input", "Luigi");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await click(".o-discuss-ChannelSelector-suggestion");
    await triggerEvent(document.body, ".o-discuss-ChannelSelector input", "keydown", {
        key: "Enter",
    });
    assert.containsN($, ".o-mail-DiscussCategoryItem", 1);
    assert.containsNone($, ".o-mail-Message");
});

QUnit.test("chat search should display no result when no matches found", async (assert) => {
    const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
    await openDiscuss();
    await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
    await insertText(".o-discuss-ChannelSelector", "Rainbow Panda");
    await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    assert.containsOnce($, ".o-discuss-ChannelSelector-suggestion:contains(No results found)");
});

QUnit.test(
    "chat search should not be visible when clicking outside of the field",
    async (assert) => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({ name: "Panda" });
        pyEnv["res.users"].create({ partner_id: partnerId });
        const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss();
        assert.containsNone($, ".o-mail-DiscussCategoryItem");
        await click(".o-mail-DiscussSidebar i[title='Start a conversation']");
        await insertText(".o-discuss-ChannelSelector", "Panda");
        await advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
        await nextTick();
        assert.containsOnce($, ".o-discuss-ChannelSelector-suggestion");
        await click(".o-mail-DiscussSidebar");
        assert.containsNone($, ".o-discuss-ChannelSelector-suggestion");
    }
);

QUnit.test("sidebar: add channel", async (assert) => {
    const { openDiscuss } = await start();
    await openDiscuss();
    assert.containsOnce($, ".o-mail-DiscussCategory-channel .o-mail-DiscussCategory-add");
    assert.hasAttrValue(
        $(".o-mail-DiscussCategory-channel .o-mail-DiscussCategory-add")[0],
        "title",
        "Add or join a channel"
    );
    await click(".o-mail-DiscussCategory-channel .o-mail-DiscussCategory-add");
    assert.containsOnce($, ".o-discuss-ChannelSelector");
    assert.containsOnce($, ".o-discuss-ChannelSelector input[placeholder='Add or join a channel']");
});

QUnit.test("Chat is added to discuss on other tab that the one that joined", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Jerry Golay" });
    pyEnv["res.users"].create({ partner_id: partnerId });
    const tab1 = await start({ asTab: true, hasTimeControl: true });
    const tab2 = await start({ asTab: true });
    await tab1.openDiscuss();
    await tab2.openDiscuss();
    await tab1.click(".o-mail-DiscussCategory-chat .o-mail-DiscussCategory-add");
    await tab1.insertText(".o-discuss-ChannelSelector input", "Jer");
    await tab1.advanceTime(DEBOUNCE_FETCH_SUGGESTION_TIME);
    await nextTick();
    await tab1.click(".o-discuss-ChannelSelector-suggestion");
    await afterNextRender(() => triggerHotkey("Enter"));
    assert.containsOnce(tab1.target, ".o-mail-DiscussCategoryItem:contains(Jerry Golay)");
    assert.containsOnce(tab2.target, ".o-mail-DiscussCategoryItem:contains(Jerry Golay)");
});
