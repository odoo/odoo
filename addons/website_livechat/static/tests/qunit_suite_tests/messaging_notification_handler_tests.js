/** @odoo-module **/

import { afterNextRender, start, startServer } from "@mail/../tests/helpers/test_utils";
import FormView from "web.FormView";

QUnit.module("website_livechat", {}, function () {
    QUnit.module("messaging_notification_handler_tests.js");

    QUnit.test(
        "should open chat window on send chat request to website visitor",
        async function (assert) {
            assert.expect(3);

            const pyEnv = await startServer();
            const websiteVisitorId1 = pyEnv["website.visitor"].create({
                display_name: "Visitor #11",
            });
            const views = {
                "website.visitor,false,form": `<form>
                <header>
                    <button name="action_send_chat_request" string="Send chat request" class="btn btn-primary" type="button"/>
                </header>
                <field name="name"/>
            </form>`,
            };

            const { openView, env } = await start({
                serverData: { views },
                View: FormView,
            });

            await openView({
                res_model: "website.visitor",
                res_id: websiteVisitorId1,
                views: [[false, "form"]],
            });

            // Simulate a click on "Send chat request"
            // This is a bit of a hack as it doesn't require the button at all to work.
            await afterNextRender(async () => {
                await env.services.rpc("/web/dataset/call_button", {
                    args: [websiteVisitorId1],
                    kwargs: { context: env.context },
                    method: "action_send_chat_request",
                    model: "website.visitor",
                });
            });

            assert.containsOnce(
                document.body,
                ".o_ChatWindow",
                "should have a chat window open after sending chat request to website visitor"
            );
            assert.hasClass(
                document.querySelector(".o_ChatWindow"),
                "o-focused",
                "chat window of livechat should be focused on open"
            );
            assert.strictEqual(
                document.querySelector(".o_ChatWindowHeader_name").textContent,
                "Visitor #11",
                "chat window of livechat should have name of visitor in the name"
            );
        }
    );
});
