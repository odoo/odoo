/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("mail", (hooks) => {
    QUnit.module("components", {}, function () {
        QUnit.module("thread_view_tests.js");

        QUnit.skipRefactoring(
            "failure on loading messages should display error",
            async function (assert) {
                assert.expect(1);

                const pyEnv = await startServer();
                const mailChannelId1 = pyEnv["mail.channel"].create({});
                const { click, insertText, openDiscuss } = await start({
                    discuss: {
                        context: { active_id: mailChannelId1 },
                    },
                });
                await openDiscuss();
                await insertText(".o-mail-composer-textarea", "Dummy Message");
                await click(".o-mail-composer-send-button");
                assert.hasClass(
                    document.querySelector(".o_ComposerView"),
                    "o-focused",
                    "composer should be focused automatically after clicking on the send button"
                );
            }
        );
    });
});
