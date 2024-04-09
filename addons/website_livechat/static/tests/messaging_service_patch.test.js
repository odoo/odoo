import { contains, openFormView, start, startServer } from "@mail/../tests/mail_test_helpers";
import { defineWebsiteLivechatModels } from "./website_livechat_test_helpers";
import { describe, test } from "@odoo/hoot";
import { getService } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("Should open chat window on send chat request to website visitor", async () => {
    const pyEnv = await startServer();
    const visitorId = pyEnv["website.visitor"].create({});
    const env = await start();
    await openFormView("website.visitor", visitorId, {
        arch: `
            <form>
                <header>
                    <button name="action_send_chat_request" string="Send chat request" class="btn btn-primary" type="button"/>
                </header>
                <field name="name"/>
            </form>`,
    });
    const store = getService("mail.store");
    await store.rpc("/web/dataset/call_button", {
        args: [visitorId],
        kwargs: { context: env.context },
        method: "action_send_chat_request",
        model: "website.visitor",
    });
    await contains(".o-mail-ChatWindow", { text: `Visitor #${visitorId}` });
    await contains(".o-mail-ChatWindow .o-mail-Composer-input:focus");
});
