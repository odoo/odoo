/** @odoo-module */

import { startServer, start, afterNextRender } from "@mail/../tests/helpers/test_utils";

QUnit.module("messaging service");

QUnit.test("Should open chat window on send chat request to website visitor", async (assert) => {
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
    assert.containsOnce($, ".o-ChatWindow");
    assert.ok(document.activeElement, $(".o-ChatWindow .o-Composer-input")[0]);
    assert.strictEqual($(".o-ChatWindow-name").text(), "Visitor #11");
});
