/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("messaging service (patch)");

QUnit.test("Should open chat window on send chat request to website visitor", async () => {
    const pyEnv = await startServer();
    const visitorId = pyEnv["website.visitor"].create({});
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
    await openFormView("website.visitor", visitorId);
    await env.services.rpc("/web/dataset/call_button", {
        args: [visitorId],
        kwargs: { context: env.context },
        method: "action_send_chat_request",
        model: "website.visitor",
    });
    await contains(".o-mail-ChatWindow", { text: `Visitor #${visitorId}` });
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:focus");
});
