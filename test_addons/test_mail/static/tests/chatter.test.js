import {
    contains,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { MockServer, onRpc } from "@web/../tests/web_test_helpers";
import { mail_thread_data } from "@mail/../tests/mock_server/mail_mock_server";

describe.current.tags("desktop");
defineTestMailModels();

test("Send message button activation (access rights dependent)", async () => {
    const pyEnv = await startServer();
    registerArchs({
        "mail.test.multi.company,false,form": `
            <form string="Simple">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>
        `,
        "mail.test.multi.company.read,false,form": `
            <form string="Simple">
                    <sheet>
                        <field name="name"/>
                    </sheet>
                    <chatter/>
                </form>
        `,
    });
    let userAccess = {};
    onRpc("/mail/thread/data", async (req) => {
        const res = await mail_thread_data.bind(MockServer.current)(req);
        res["mail.thread"][0].hasWriteAccess = userAccess.hasWriteAccess;
        res["mail.thread"][0].hasReadAccess = userAccess.hasReadAccess;
        return res;
    });
    await start();
    const simpleId = pyEnv["mail.test.multi.company"].create({ name: "Test MC Simple" });
    const simpleMcId = pyEnv["mail.test.multi.company.read"].create({
        name: "Test MC Readonly",
    });
    async function assertSendButton(
        enabled,
        msg,
        model = null,
        resId = null,
        hasReadAccess = false,
        hasWriteAccess = false
    ) {
        userAccess = { hasReadAccess, hasWriteAccess };
        await openFormView(model, resId);
        if (enabled) {
            await contains(".o-mail-Chatter-topbar button:enabled", { text: "Send message" });
        } else {
            await contains(".o-mail-Chatter-topbar button:disabled", { text: "Send message" });
        }
    }
    await assertSendButton(
        true,
        "Record, all rights",
        "mail.test.multi.company",
        simpleId,
        true,
        true
    );
    await assertSendButton(
        true,
        "Record, all rights",
        "mail.test.multi.company.read",
        simpleId,
        true,
        true
    );
    await assertSendButton(
        false,
        "Record, no write access",
        "mail.test.multi.company",
        simpleId,
        true
    );
    await assertSendButton(
        true,
        "Record, read access but model accept post with read only access",
        "mail.test.multi.company.read",
        simpleMcId,
        true
    );
    await assertSendButton(false, "Record, no rights", "mail.test.multi.company", simpleId);
    await assertSendButton(false, "Record, no rights", "mail.test.multi.company.read", simpleMcId);
    // Note that rights have no impact on send button for draft record (chatter.isTemporary=true)
    await assertSendButton(true, "Draft record", "mail.test.multi.company");
    await assertSendButton(true, "Draft record", "mail.test.multi.company.read");
});

test("basic chatter rendering with a model without activities", async () => {
    const pyEnv = await startServer();
    const recordId = pyEnv["mail.test.simple"].create({ name: "new record" });
    registerArchs({
        "mail.test.simple,false,form": `
            <form string="Records">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>
        `,
    });
    await start();
    await openFormView("mail.test.simple", recordId);
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains("button[aria-label='Attach files']");
    await contains("button", { count: 0, text: "Activities" });
    await contains(".o-mail-Followers");
    await contains(".o-mail-Thread");
});
