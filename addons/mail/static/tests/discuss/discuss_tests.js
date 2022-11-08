/** @odoo-module **/

import { Discuss } from "@mail/discuss/discuss";
import { click, editInput, getFixture, mount, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeMessagingEnv, MessagingServer } from "../helpers/helpers";
import { browser } from "@web/core/browser/browser";

let target;

QUnit.module("mail", (hooks) => {
    hooks.beforeEach(async () => {
        target = getFixture();
        // for autocomplete stuff
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("discuss");

    QUnit.test("sanity check", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => {
            if (route.startsWith('/mail')) {
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
        const server = new MessagingServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeMessagingEnv((route, params) => {
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

    QUnit.test("can post a message", async (assert) => {
        const server = new MessagingServer();
        server.addChannel(1, "general", "General announcements...");
        const env = makeMessagingEnv((route, params) => {
            if (route.startsWith('/mail')) {
                assert.step(route);
            }
            return server.rpc(route, params);
        });
        env.services["mail.messaging"].setDiscussThread(1);

        await mount(Discuss, target, { env });
        assert.containsNone(target, ".o-mail-message");
        await editInput(target, ".o-mail-composer-textarea", "abc");
        await click($(target).find(".o-mail-composer button:contains('Send')")[0]); // click on send
        assert.containsOnce(target, ".o-mail-message");
        assert.verifySteps([
            "/mail/init_messaging",
            "/mail/channel/messages",
            "/mail/message/post",
        ]);
    });

    QUnit.test("can create a new channel", async (assert) => {
        const server = new MessagingServer();
        const env = makeMessagingEnv((route, params) => {
            if (
                route.startsWith('/mail') ||
                ["/web/dataset/call_kw/mail.channel/search_read", "/web/dataset/call_kw/mail.channel/channel_create"].includes(route)
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
        const server = new MessagingServer();
        server.addPartner(43, "abc");
        const env = makeMessagingEnv((route, params) => {
            if (
                route.startsWith('/mail') ||
                ["/web/dataset/call_kw/res.partner/im_search", "/web/dataset/call_kw/mail.channel/channel_get"].includes(route)
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
        const server = new MessagingServer();
        server.addChannel(1, "general", "General announcements...");
        server.addChannel(2, "other", "info");
        const env = makeMessagingEnv((route, params) => server.rpc(route, params));

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
});
