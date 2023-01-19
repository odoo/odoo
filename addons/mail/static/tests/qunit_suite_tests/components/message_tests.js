/** @odoo-module **/

import { nextAnimationFrame, start, startServer } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("mail", {}, function () {
    QUnit.module("components", {}, function () {
        QUnit.module("message_tests.js");

        QUnit.skipRefactoring(
            "data-oe-id & data-oe-model link redirection on click",
            async function (assert) {
                assert.expect(7);

                const pyEnv = await startServer();
                const threadId = pyEnv["res.partner"].create({});
                pyEnv["mail.message"].create({
                    body: `<p><a href="#" data-oe-id="250" data-oe-model="some.model">some.model_250</a></p>`,
                    model: "res.partner",
                    res_id: threadId,
                });
                const { env, openView } = await start();
                await openView({
                    res_id: threadId,
                    res_model: "res.partner",
                    views: [[false, "form"]],
                });
                patchWithCleanup(env.services.action, {
                    doAction(action) {
                        assert.strictEqual(
                            action.type,
                            "ir.actions.act_window",
                            "action should open view"
                        );
                        assert.strictEqual(
                            action.res_model,
                            "some.model",
                            "action should open view on 'some.model' model"
                        );
                        assert.strictEqual(action.res_id, 250, "action should open view on 250");
                        assert.step("do-action:openFormView_some.model_250");
                    },
                });
                assert.containsOnce(
                    document.body,
                    ".o-mail-message-body",
                    "message should have content"
                );
                assert.containsOnce(
                    document.querySelector(".o-mail-message-body"),
                    "a",
                    "message content should have a link"
                );

                document.querySelector(`.o-mail-message-body a`).click();
                assert.verifySteps(
                    ["do-action:openFormView_some.model_250"],
                    "should have open form view on related record after click on link"
                );
            }
        );

        QUnit.skipRefactoring(
            "open chat with author on avatar click should be disabled when currently chatting with the author",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const resPartnerId = pyEnv["res.partner"].create({});
                pyEnv["res.users"].create({ partner_id: resPartnerId });
                const mailChannelId = pyEnv["mail.channel"].create({
                    channel_member_ids: [
                        [0, 0, { partner_id: pyEnv.currentPartnerId }],
                        [0, 0, { partner_id: resPartnerId }],
                    ],
                    channel_type: "chat",
                });
                pyEnv["mail.message"].create({
                    author_id: resPartnerId,
                    body: "not empty",
                    model: "mail.channel",
                    res_id: mailChannelId,
                });
                const { openDiscuss } = await start({
                    discuss: {
                        params: {
                            default_active_id: `mail.channel_${mailChannelId}`,
                        },
                    },
                });
                await openDiscuss();
                assert.containsOnce(
                    document.body,
                    ".o-mail-message-author-avatar",
                    "message should have the author avatar"
                );
                assert.doesNotHaveClass(
                    document.querySelector(".o-mail-message-author-avatar"),
                    "o_redirect",
                    "author avatar should not have the redirect style"
                );

                document.querySelector(".o-mail-message-author-avatar").click();
                await nextAnimationFrame();
                assert.containsNone(
                    document.body,
                    ".o-mail-chat-window",
                    "should have no thread opened after clicking on author avatar when currently chatting with the author"
                );
            }
        );

        QUnit.skipRefactoring(
            "Chat with partner should be opened after clicking on their mention",
            async function (assert) {
                assert.expect(2);

                const pyEnv = await startServer();
                const resPartnerId = pyEnv["res.partner"].create({
                    name: "Test Partner",
                    email: "testpartner@odoo.com",
                });
                pyEnv["res.users"].create({ partner_id: resPartnerId });
                const { click, insertText, openFormView } = await start();
                await openFormView("res.partner", resPartnerId);
                await click("button:contains(Send message)");
                await insertText(".o-mail-composer-textarea", "@Te");
                await click(".o_ComposerSuggestionView");
                await click(".o-mail-composer-send-button");
                await click(".o_mail_redirect");
                assert.containsOnce(
                    document.body,
                    ".o_ChatWindow_thread",
                    "chat window with thread should be opened after clicking on partner mention"
                );
                assert.strictEqual(
                    document.querySelector(".o_ChatWindow_thread").dataset.correspondentId,
                    resPartnerId.toString(),
                    "chat with partner should be opened after clicking on their mention"
                );
            }
        );

        QUnit.skipRefactoring(
            "Channel should be opened after clicking on its mention",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const resPartnerId = pyEnv["res.partner"].create({});
                pyEnv["mail.channel"].create({ name: "my-channel" });
                const { click, insertText, openFormView } = await start();
                await openFormView("res.partner", resPartnerId);
                await click("button:contains(Send message)");
                await insertText(".o-mail-composer-textarea", "#my-channel");
                await click(".o_ComposerSuggestionView");
                await click(".o-mail-composer-send-button");
                await click(".o_channel_redirect");
                assert.containsOnce(
                    document.body,
                    ".o_ChatWindow_thread",
                    "chat window with thread should be opened after clicking on channel mention"
                );
            }
        );
    });
});
