/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", (hooks) => {
    QUnit.module("components", {}, function () {
        QUnit.module("discuss_inbox_tests.js");

        QUnit.skipRefactoring("reply: discard on discard button click", async function (assert) {
            assert.expect(4);

            const pyEnv = await startServer();
            const resPartnerId1 = pyEnv["res.partner"].create({});
            const mailMessageId1 = pyEnv["mail.message"].create({
                body: "not empty",
                model: "res.partner",
                needaction: true,
                needaction_partner_ids: [pyEnv.currentPartnerId],
                res_id: resPartnerId1,
            });
            pyEnv["mail.notification"].create({
                mail_message_id: mailMessageId1,
                notification_status: "sent",
                notification_type: "inbox",
                res_partner_id: pyEnv.currentPartnerId,
            });
            const { click, openDiscuss } = await start();
            await openDiscuss();
            assert.containsOnce(
                document.body,
                ".o-mail-message",
                "should display a single message"
            );

            await click("i[aria-label='Reply']");
            assert.containsOnce(
                document.body,
                ".o-mail-composer",
                "should have composer after clicking on reply to message"
            );
            assert.containsOnce(
                document.body,
                "i[title='Stop replying']",
                "composer should have a discard button"
            );

            await click("i[title='Stop replying']");
            assert.containsNone(
                document.body,
                ".o-mail-composer",
                "reply composer should be closed after clicking on discard"
            );
        });

        QUnit.skipRefactoring(
            "error notifications should not be shown in Inbox",
            async function (assert) {
                assert.expect(3);

                const pyEnv = await startServer();
                const resPartnerId1 = pyEnv["res.partner"].create({});
                const mailMessageId1 = pyEnv["mail.message"].create({
                    body: "not empty",
                    model: "mail.channel",
                    needaction: true,
                    needaction_partner_ids: [pyEnv.currentPartnerId],
                    res_id: resPartnerId1,
                });
                pyEnv["mail.notification"].create({
                    mail_message_id: mailMessageId1, // id of related message
                    notification_status: "exception",
                    notification_type: "email",
                    res_partner_id: pyEnv.currentPartnerId, // must be for current partner
                });
                const { openDiscuss } = await start();
                await openDiscuss();
                assert.containsOnce(
                    document.body,
                    ".o-mail-message",
                    "should display a single message"
                );
                assert.containsOnce(
                    document.body,
                    ".o_MessageView_originThreadLink",
                    "should display origin thread link"
                );
                assert.containsNone(
                    document.body,
                    ".o-mail-message-notification-icon",
                    "should not display any notification icon in Inbox"
                );
            }
        );
    });
});
