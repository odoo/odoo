/** @odoo-module */

import { getFixture } from "@web/../tests/helpers/utils";
import { startServer, start, afterNextRender } from "@mail/../tests/helpers/test_utils";

let target;
QUnit.module("messaging service", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test(
    "Should open chat window on send chat request to website visitor",
    async function (assert) {
        const pyEnv = await startServer();
        const visitorId = pyEnv["website.visitor"].create({
            display_name: "Visitor #11",
        });
        const { env, openFormView } = await start({
            serverData: {
                views: {
                    "website.visitor,false,form": `
                    <form>
                        <header>
                            <button name="action_send_chat_request" string="Send chat request" class="btn btn-primary" type="button"/>
                        </header>
                        <field name="name"/>
                    </form>`,
                },
            },
        });
        await openFormView("website.visitor", visitorId, {
            waitUntilDataLoaded: false,
            waitUntilMessagesLoaded: false,
        });
        await afterNextRender(async () => {
            await env.services.rpc("/web/dataset/call_button", {
                args: [visitorId],
                kwargs: { context: env.context },
                method: "action_send_chat_request",
                model: "website.visitor",
            });
        });
        assert.containsOnce(target, ".o-mail-chat-window");
        assert.ok(
            document.activeElement,
            target.querySelector(".o-mail-chat-window .o-mail-composer-textarea")
        );
        assert.strictEqual(
            document.querySelector(".o-mail-chat-window-header-name").textContent,
            "Visitor #11"
        );
    }
);
