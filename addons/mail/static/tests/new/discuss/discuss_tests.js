/** @odoo-module **/

import { Discuss } from "@mail/new/discuss/discuss";
import { start, startServer, afterNextRender } from "@mail/../tests/helpers/test_utils";
import {
    click,
    editInput,
    getFixture,
    mount,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { insertText, makeTestEnv, TestServer } from "../helpers/helpers";
import { browser } from "@web/core/browser/browser";
import { loadEmoji } from "@mail/new/composer/emoji_picker";
import { UPDATE_BUS_PRESENCE_DELAY } from "@bus/im_status_service";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
    });

    QUnit.module("discuss");

    QUnit.test("sanity check", async (assert) => {
        const server = new TestServer();
        const env = makeTestEnv((route, params) => {
            if (route.startsWith("/mail")) {
                assert.step(route);
            }
            return server.rpc(route, params);
        });

        await mount(Discuss, target, { env });
        assert.containsOnce(target, ".o-mail-discuss-sidebar");
        assert.containsOnce(
            target,
            ".o-mail-discuss-content h4:contains(Congratulations, your inbox is empty)"
        );

        assert.verifySteps(["/mail/init_messaging", "/mail/inbox/messages"]);
    });

    QUnit.test("can open #general", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeTestEnv((route, params) => {
            if (route === "/mail/channel/messages") {
                assert.strictEqual(route, "/mail/channel/messages");
                assert.strictEqual(params.channel_id, 1);
                assert.strictEqual(params.limit, 30);
            }
            return server.rpc(route, params);
        });

        await mount(Discuss, target, { env });
        assert.containsOnce(target, ".o-mail-category-item");
        assert.containsNone(target, ".o-mail-category-item.o-active");
        await click(target, ".o-mail-category-item");
        assert.containsOnce(target, ".o-mail-category-item.o-active");
        assert.containsNone(target, ".o-mail-discuss-content .o-mail-message");
        assert.strictEqual(
            target.querySelector(".o-mail-composer-textarea"),
            document.activeElement
        );
    });

    QUnit.test("can change the thread name of #general", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeTestEnv((route, params) => {
            if (route === "/web/dataset/call_kw/mail.channel/channel_rename") {
                assert.step(route);
            }
            return server.rpc(route, params);
        });
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        assert.containsOnce(target, "input.o-mail-discuss-thread-name");
        const threadNameElement = target.querySelector("input.o-mail-discuss-thread-name");

        await click(threadNameElement);
        assert.strictEqual(threadNameElement.value, "general");
        await editInput(target, "input.o-mail-discuss-thread-name", "special");
        await triggerEvent(target, "input.o-mail-discuss-thread-name", "keydown", {
            key: "Enter",
        });
        assert.strictEqual(threadNameElement.value, "special");

        assert.verifySteps(["/web/dataset/call_kw/mail.channel/channel_rename"]);
    });

    QUnit.test("can change the thread description of #general", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeTestEnv((route, params) => {
            if (route === "/web/dataset/call_kw/mail.channel/channel_change_description") {
                assert.step(route);
            }
            return server.rpc(route, params);
        });
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });

        assert.containsOnce(target, "input.o-mail-discuss-thread-description");
        const threadDescriptionElement = target.querySelector(
            "input.o-mail-discuss-thread-description"
        );

        await click(threadDescriptionElement);
        assert.strictEqual(threadDescriptionElement.value, "General announcements...");
        await editInput(
            target,
            "input.o-mail-discuss-thread-description",
            "I want a burger today!"
        );
        await triggerEvent(target, "input.o-mail-discuss-thread-description", "keydown", {
            key: "Enter",
        });
        assert.strictEqual(threadDescriptionElement.value, "I want a burger today!");

        assert.verifySteps(["/web/dataset/call_kw/mail.channel/channel_change_description"]);
    });

    QUnit.test("can post a message", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeTestEnv((route, params) => {
            if (route.startsWith("/mail")) {
                assert.step(route);
            }
            return server.rpc(route, params);
        });
        env.services["mail.messaging"].setDiscussThread(1);

        await mount(Discuss, target, { env });
        assert.containsNone(target, ".o-mail-message");
        await insertText(".o-mail-composer-textarea", "abc");
        await click(target, ".o-mail-composer-send-button");
        await loadEmoji(); // wait for emoji being loaded (required for rendering)
        await nextTick(); // wait for following rendering
        assert.containsOnce(target, ".o-mail-message");
        assert.verifySteps([
            "/mail/init_messaging",
            "/mail/channel/messages",
            "/mail/message/post",
            "/mail/link_preview",
        ]);
    });

    QUnit.test("can create a new channel", async (assert) => {
        // for autocomplete stuff
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
        const server = new TestServer();
        const env = makeTestEnv((route, params) => {
            if (
                route.startsWith("/mail") ||
                [
                    "/web/dataset/call_kw/mail.channel/search_read",
                    "/web/dataset/call_kw/mail.channel/channel_create",
                ].includes(route)
            ) {
                assert.step(route);
            }
            return server.rpc(route, params);
        });
        await mount(Discuss, target, { env });
        assert.containsNone(target, ".o-mail-category-item");
        await click(target, ".o-mail-discuss-sidebar i[title='Add or join a channel']");
        await editInput(target, ".o-autocomplete--input", "abc");
        await click(target, ".o-mail-discuss-sidebar .o-autocomplete--dropdown-item");
        assert.containsN(target, ".o-mail-category-item", 1);
        assert.containsN(target, ".o-mail-discuss-content .o-mail-message", 0);
        assert.verifySteps([
            "/mail/init_messaging",
            "/mail/inbox/messages",
            "/web/dataset/call_kw/mail.channel/search_read",
            "/web/dataset/call_kw/mail.channel/channel_create",
            "/mail/channel/messages",
        ]);
    });

    QUnit.test("can join a chat conversation", async (assert) => {
        // for autocomplete stuff
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
        const server = new TestServer();
        server.addPartner(43, "abc");
        const env = makeTestEnv((route, params) => {
            if (
                route.startsWith("/mail") ||
                [
                    "/web/dataset/call_kw/res.partner/im_search",
                    "/web/dataset/call_kw/mail.channel/channel_get",
                ].includes(route)
            ) {
                assert.step(route);
            }
            if (route === "/web/dataset/call_kw/mail.channel/channel_get") {
                assert.equal(params.kwargs.partners_to[0], 43);
            }
            return server.rpc(route, params);
        });

        await mount(Discuss, target, { env });
        assert.containsNone(target, ".o-mail-category-item");
        await click(target, ".o-mail-discuss-sidebar i[title='Start a conversation']");
        await editInput(target, ".o-autocomplete--input", "abc");
        await click(target, ".o-mail-discuss-sidebar .o-autocomplete--dropdown-item");
        assert.containsN(target, ".o-mail-category-item", 1);
        assert.containsNone(target, ".o-mail-discuss-content .o-mail-message");
        assert.verifySteps([
            "/mail/init_messaging",
            "/mail/inbox/messages",
            "/web/dataset/call_kw/res.partner/im_search",
            "/web/dataset/call_kw/mail.channel/channel_get",
            "/mail/channel/messages",
        ]);
    });

    QUnit.test("focus is set on composer when switching channel", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addChannel(2, "other", "info");
        const env = makeTestEnv((route, params) => server.rpc(route, params));

        await mount(Discuss, target, { env });
        assert.containsNone(target, ".o-mail-composer-textarea");
        assert.containsN(target, ".o-mail-category-item", 2);

        // switch to first channel and check focus is correct
        await click(target.querySelectorAll(".o-mail-category-item")[0]);
        assert.containsOnce(target, ".o-mail-composer-textarea");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o-mail-composer-textarea")
        );

        // unfocus composer, then switch on second channel and see if focus is correct
        target.querySelector(".o-mail-composer-textarea").blur();
        assert.strictEqual(document.activeElement, document.body);
        await click(target.querySelectorAll(".o-mail-category-item")[1]);
        assert.containsOnce(target, ".o-mail-composer-textarea");
        assert.strictEqual(
            document.activeElement,
            target.querySelector(".o-mail-composer-textarea")
        );
    });

    QUnit.test("Message following a notification should not be squashed", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        server.addMessage(
            "notification",
            1,
            1,
            "mail.channel",
            3,
            '<div class="o_mail_notification">created <a href="#" class="o_channel_redirect">#general</a></div>'
        );
        server.addMessage("comment", 2, 1, "mail.channel", 3, "Hello world !");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        await env.services["mail.messaging"].isReady;
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });

        assert.containsOnce(target, ".o-mail-message-sidebar .o-mail-avatar-container");
    });

    QUnit.test("Posting message should transform links.", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        await insertText(".o-mail-composer-textarea", "test https://www.odoo.com/");
        await click(target, ".o-mail-composer-send-button");
        await loadEmoji(); // wait for emoji being loaded (required for rendering)
        await nextTick(); // wait for following rendering
        assert.containsOnce(
            target,
            "a[href='https://www.odoo.com/']",
            "Message should have a link"
        );
    });

    QUnit.test("Posting message should transform relevant data to emoji.", async (assert) => {
        const server = new TestServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeTestEnv((route, params) => server.rpc(route, params));
        env.services["mail.messaging"].setDiscussThread(1);
        await mount(Discuss, target, { env });
        await insertText(".o-mail-composer-textarea", "test :P :laughing:");
        await click(target, ".o-mail-composer-send-button");
        await loadEmoji(); // wait for emoji being loaded (required for rendering)
        await nextTick(); // wait for following rendering
        assert.equal(target.querySelector(".o-mail-message-body").textContent, "test 😛 😆");
    });

    QUnit.test(
        "posting a message immediately after another one is displayed in 'simple' mode (squashed)",
        async (assert) => {
            let flag = false;
            const server = new TestServer();
            server.addChannel(1, "general", "General announcements...");
            const env = makeTestEnv(async (route, params) => {
                if (flag && route === "/mail/message/post") {
                    await new Promise(() => {});
                }
                return server.rpc(route, params);
            });
            env.services["mail.messaging"].setDiscussThread(1);

            await mount(Discuss, target, { env });
            // write 1 message
            await editInput(target, ".o-mail-composer-textarea", "abc");
            await click(target, ".o-mail-composer button[data-action='send']");

            // write another message, but /mail/message/post is delayed by promise
            flag = true;
            await editInput(target, ".o-mail-composer-textarea", "def");
            await click(target, ".o-mail-composer button[data-action='send']");
            assert.containsN(target, ".o-mail-message", 2);
            assert.containsN(target, ".o-mail-msg-header", 1); // just 1, because 2nd message is squashed
        }
    );

    QUnit.test("Click on avatar opens its partner chat window", async (assert) => {
        assert.expect(3);
        const pyEnv = await startServer();
        const testPartnerId = pyEnv["res.partner"].create({
            name: "testPartner",
        });
        pyEnv["mail.message"].create({
            author_id: testPartnerId,
            body: "Test",
            attachment_ids: [],
            model: "res.partner",
            res_id: testPartnerId,
        });
        const { openFormView } = await start();
        await openFormView({
            res_id: testPartnerId,
            res_model: "res.partner",
        });
        assert.containsOnce(
            target,
            ".o-mail-message-sidebar .o-mail-avatar-container .cursor-pointer"
        );
        await click(
            target.querySelector(".o-mail-message-sidebar .o-mail-avatar-container .cursor-pointer")
        );
        assert.containsOnce(target, ".o-mail-chat-window-header-name");
        assert.ok(
            target
                .querySelector(".o-mail-chat-window-header-name")
                .textContent.includes("testPartner")
        );
    });

    QUnit.test("Can use channel command /who", async (assert) => {
        assert.expect(1);

        const pyEnv = await startServer();
        const mailChannelId1 = pyEnv["mail.channel"].create({
            channel_type: "channel",
            name: "my-channel",
        });
        const { click, insertText, openDiscuss } = await start({
            discuss: {
                params: {
                    default_active_id: mailChannelId1,
                },
            },
        });
        await openDiscuss();
        await insertText(".o-mail-composer-textarea", "/who");
        await click(".o-mail-composer button[data-action='send']");

        assert.strictEqual(
            document.querySelector(`.o_mail_notification`).textContent,
            "You are alone in this channel.",
            "should display '/who' result"
        );
    });

    QUnit.test("sidebar: chat im_status rendering", async function (assert) {
        assert.expect(8);

        const pyEnv = await startServer();
        const [resPartnerId1, resPartnerId2, resPartnerId3] = pyEnv["res.partner"].create([
            { im_status: "offline", name: "Partner1" },
            { im_status: "online", name: "Partner2" },
            { im_status: "away", name: "Partner3" },
        ]);
        pyEnv["mail.channel"].create([
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: resPartnerId1 }],
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: resPartnerId2 }],
                ],
                channel_type: "chat",
            },
            {
                channel_member_ids: [
                    [0, 0, { partner_id: pyEnv.currentPartnerId }],
                    [0, 0, { partner_id: resPartnerId3 }],
                ],
                channel_type: "chat",
            },
        ]);
        const { advanceTime, openDiscuss } = await start({ hasTimeControl: true });
        await openDiscuss();
        await afterNextRender(() => advanceTime(UPDATE_BUS_PRESENCE_DELAY));
        assert.strictEqual(
            target.querySelectorAll(".o-mail-category-item").length,
            3,
            "should have 3 category items"
        );
        assert.strictEqual(
            target.querySelectorAll(
                ".o-mail-category-item .o-mail-category-im-status .o-mail-partner-im-status"
            ).length,
            3,
            "should have 3 partner im-status"
        );
        const chat1 = target.querySelectorAll(".o-mail-category-item")[0];
        const chat2 = target.querySelectorAll(".o-mail-category-item")[1];
        const chat3 = target.querySelectorAll(".o-mail-category-item")[2];
        assert.strictEqual(chat1.textContent, "Partner1", "First chat should have Partner1");
        assert.strictEqual(chat2.textContent, "Partner2", "First chat should have Partner2");
        assert.strictEqual(chat3.textContent, "Partner3", "First chat should have Partner3");
        assert.strictEqual(
            chat1.querySelectorAll(".o-offline").length,
            1,
            "chat1 should have offline icon"
        );
        assert.strictEqual(
            chat2.querySelectorAll(".o-online").length,
            1,
            "chat2 should have online icon"
        );
        assert.strictEqual(
            chat3.querySelectorAll(".o-away").length,
            1,
            "chat3 should have away icon"
        );
    });
});
