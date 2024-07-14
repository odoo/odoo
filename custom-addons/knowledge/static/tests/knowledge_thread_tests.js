/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addModelNamesToFetch } from "@bus/../tests/helpers/model_definitions_helpers";
import { start } from "@mail/../tests/helpers/test_utils";
import { click, contains } from "@web/../tests/utils";
import { makeDeferred, patchWithCleanup } from "@web/../tests/helpers/utils";

QUnit.module("Knowledge - Thread tests");

addModelNamesToFetch(["knowledge.article", "knowledge.article.thread"]);

QUnit.test("Expand article.thread opens linked article", async function (assert) {
    const pyEnv = await startServer();
    const actionPromise = makeDeferred();

    const { env } = await start();

    patchWithCleanup(env.services.action, {
        doAction(action, params) {
            assert.ok(params?.additionalContext?.res_id);
            assert.strictEqual(action, "knowledge.ir_actions_server_knowledge_home_page");
            assert.step("knowledge_action_called");
            actionPromise.resolve();
        },
    });

    const articleId = pyEnv["knowledge.article"].create({
        name: "Thread tests",
        body: `
            <h1>Thread tests</h1>
            <p>Hello World</p>
        `,
    });

    const thread = pyEnv["knowledge.article.thread"].create({
        article_id: articleId,
    });

    pyEnv["bus.bus"]._sendone(pyEnv.currentPartner, "mail.message/inbox", {
        author_id: pyEnv.publicPartnerId,
        body: "Howdy Neighbor",
        id: thread,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        model: "knowledge.article.thread",
        res_id: thread,
        record_name: "Thread tests",
    });

    await contains(".o-mail-MessagingMenu-counter", { text: "1" });
    await click(".o-mail-DiscussSystray-class .fa-comments");
    await click(".o-mail-NotificationItem");
    await contains(".o-mail-ChatWindow-header", { text: "Thread tests" });
    await click(".o-mail-ChatWindow-command[title='Open Form View']");
    await actionPromise;
    await assert.verifySteps(["knowledge_action_called"]);
    await contains(".o-mail-ChatWindow-header", { count: 0 });
});
