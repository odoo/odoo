import {
    click,
    contains,
    inputFiles,
    insertText,
    listenStoreFetch,
    openFormView,
    patchUiSize,
    registerArchs,
    SIZES,
    start,
    startServer,
    triggerHotkey,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { MockServer, onRpc } from "@web/../tests/web_test_helpers";
import { mail_data } from "@mail/../tests/mock_server/mail_mock_server";

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
    listenStoreFetch("mail.thread", {
        async onRpc(request) {
            const { params } = await request.json();
            if (params.fetch_params.some((fetchParam) => fetchParam[0] === "mail.thread")) {
                const res = await mail_data.bind(MockServer.current)(request);
                res["mail.thread"][0].hasWriteAccess = userAccess.hasWriteAccess;
                res["mail.thread"][0].hasReadAccess = userAccess.hasReadAccess;
                return res;
            }
        },
    });
    await start();
    const simpleId = pyEnv["mail.test.multi.company"].create({ name: "Test MC Simple" });
    const simpleMcId = pyEnv["mail.test.multi.company.read"].create({
        name: "Test MC Readonly with Activities",
    });
    async function assertSendButton(
        enabled,
        activities,
        msg,
        model = null,
        resId = null,
        hasReadAccess = false,
        hasWriteAccess = false
    ) {
        userAccess = { hasReadAccess, hasWriteAccess };
        await openFormView(model, resId);
        if (resId) {
            await waitStoreFetch("mail.thread");
        }
        if (enabled) {
            await contains(".o-mail-Chatter-topbar button:enabled", { text: "Send message" });
            await contains(".o-mail-Chatter-topbar button:enabled", { text: "Log note" });
            if (activities) {
                await contains(".o-mail-Chatter-topbar button:enabled", { text: "Activity" });

            }
        } else {
            await contains(".o-mail-Chatter-topbar button:disabled", { text: "Send message" });
            await contains(".o-mail-Chatter-topbar button:disabled", { text: "Log note" });
            if (activities) {
                await contains(".o-mail-Chatter-topbar button:disabled", { text: "Activity" });

            }
        }
    }
    await assertSendButton(
        true,
        false,
        "Record, all rights",
        "mail.test.multi.company",
        simpleId,
        true,
        true
    );
    await assertSendButton(
        true,
        true,
        "Record, all rights",
        "mail.test.multi.company.read",
        simpleId,
        true,
        true
    );
    await assertSendButton(
        false,
        false,
        "Record, no write access",
        "mail.test.multi.company",
        simpleId,
        true
    );
    await assertSendButton(
        true,
        true,
        "Record, read access but model accept post with read only access",
        "mail.test.multi.company.read",
        simpleMcId,
        true
    );
    await assertSendButton(false, false, "Record, no rights", "mail.test.multi.company", simpleId);
    await assertSendButton(false, true, "Record, no rights", "mail.test.multi.company.read", simpleMcId);
    // Note that rights have no impact on send button for draft record (chatter.isTemporary=true)
    await assertSendButton(true, false, "Draft record", "mail.test.multi.company");
    await assertSendButton(true, true, "Draft record", "mail.test.multi.company.read");
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

test("opened attachment box should remain open after adding a new attachment", async (assert) => {
    const pyEnv = await startServer();
    const recordId = pyEnv["mail.test.simple.main.attachment"].create({});
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_id: recordId,
        res_model: "mail.test.simple.main.attachment",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        model: "mail.test.simple.main.attachment",
        res_id: recordId,
    });
    onRpc("/mail/thread/data", async (request) => {
        await new Promise((resolve) => setTimeout(resolve, 1)); // need extra time for useEffect
    });
    patchUiSize({ size: SIZES.XXL });
    await start();
    await openFormView("mail.test.simple.main.attachment", recordId, {
        arch: `
            <form>
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview" />
                <chatter reload_on_post="True" reload_on_attachment="True"/>
            </form>`,
    });
    await contains(".o_attachment_preview");
    await click(".o-mail-Chatter-attachFiles");
    await contains(".o-mail-AttachmentBox");
    await click("button", { text: "Send message" });
    await inputFiles(".o-mail-Composer .o_input_file", [
        new File(["image"], "testing.jpeg", { type: "image/jpeg" }),
    ]);
    await click(".o-mail-Composer-send:enabled");
    await contains(".o_move_next");
    await click("button", { text: "Send message" });
    await insertText(".o-mail-Composer-input", "test");
    triggerHotkey("control+Enter");
    await contains(".o-mail-Message-body", { text: "test" });
    await contains(".o-mail-AttachmentBox .o-mail-AttachmentImage", { count: 2 });
});
