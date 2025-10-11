/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, createFile, inputFiles, insertText } from "@web/../tests/utils";

QUnit.module("chatter");

QUnit.test("Messaging buttons activation (access rights dependent)", async function (assert) {
    const pyEnv = await startServer();
    const view = `
        <form string="Simple">
            <sheet>
                <field name="name"/>
            </sheet>
            <div class="oe_chatter">
                <field name="message_ids"/>
            </div>
        </form>`;
    let userAccess = {};
    const { openView } = await start({
        serverData: {
            views: {
                "mail.test.multi.company,false,form": view,
                "mail.test.multi.company.read,false,form": view,
            },
        },
        async mockRPC(route, args, performRPC) {
            const res = await performRPC(route, args);
            if (route === "/mail/thread/data") {
                // mimic user with custom access defined in userAccess variable
                const { thread_model } = args;
                Object.assign(res, userAccess);
                res["canPostOnReadonly"] = thread_model === "mail.test.multi.company.read";
            }
            return res;
        },
    });
    const simpleId = pyEnv["mail.test.multi.company"].create({
        name: "Test MC Simple"
    });
    const simpleMcId = pyEnv["mail.test.multi.company.read"].create({
        name: "Test MC Readonly",
    });
    async function assertChatterButton(
        text,
        enabled,
        msg,
        model = null,
        resId = null,
        hasReadAccess = false,
        hasWriteAccess = false
    ) {
        userAccess = { hasReadAccess, hasWriteAccess };
        await openView({
            res_id: resId,
            res_model: model,
            views: [[false, "form"]],
        });
        if (enabled) {
            await contains(".o-mail-Chatter-topbar button:enabled", { text: text });
        } else {
            await contains(".o-mail-Chatter-topbar button:disabled", { text: text });
        }
    }

    const params = [
        [true, "Record, all rights", "mail.test.multi.company", simpleId, true, true],
        [true, "Record, all rights", "mail.test.multi.company.read", simpleId, true, true],
        [false, "Record, no write access", "mail.test.multi.company", simpleId, true],
        [true, "Record, read access but model accept post with read only access",
            "mail.test.multi.company.read", simpleMcId, true],
        [false, "Record, no rights", "mail.test.multi.company", simpleId],
        [false, "Record, no rights", "mail.test.multi.company.read", simpleMcId],
        // Note that rights have no impact on send button for draft record (chatter.isTemporary=true)
        [true, "Draft record", "mail.test.multi.company"],
        [true, "Draft record", "mail.test.multi.company.read"],
    ];

    for (const text of ["Send message", "Log note"]) {
        for (const [enabled, description, model, resId, read = false, write = false] of params) {
            await assertChatterButton(text, enabled, description, model, resId, read, write);
        }
    }
});

QUnit.test("Activity buttons activation (access rights dependent)", async function (assert) {
    const pyEnv = await startServer();
    const view = `
        <form string="Simple">
            <sheet>
                <field name="name"/>
            </sheet>
            <div class="oe_chatter">
                <field name="activity_ids"/>
            </div>
        </form>`;
    let userAccess = {};
    const { openView } = await start({
        serverData: {
            views: {
                "mail.test.multi.company.with.activity,false,form": view,
                "mail.test.multi.company.with.activity.read,false,form": view,
            },
        },
        async mockRPC(route, args, performRPC) {
            const res = await performRPC(route, args);
            if (route === "/mail/thread/data") {
                // mimic user with custom access defined in userAccess variable
                const { thread_model } = args;
                Object.assign(res, userAccess);
                res["canPostOnReadonly"] = thread_model === "mail.test.multi.company.with.activity.read";
            }
            return res;
        },
    });
    const simpleId = pyEnv["mail.test.multi.company.with.activity"].create({
        name: "Test MC with activities",
    });
    const simpleMcId = pyEnv["mail.test.multi.company.with.activity.read"].create({
        name: "Test MC with activities Readonly",
    });
    async function assertChatterButton(
        text,
        enabled,
        msg,
        model = null,
        resId = null,
        hasReadAccess = false,
        hasWriteAccess = false
    ) {
        userAccess = { hasReadAccess, hasWriteAccess };
        await openView({
            res_id: resId,
            res_model: model,
            views: [[false, "form"]],
        });
        if (enabled) {
            await contains(".o-mail-Chatter-topbar button:enabled span", { text: text });
        } else {
            await contains(".o-mail-Chatter-topbar button:disabled span", { text: text });
        }
    }

    const params = [
        [true, "Record, all rights", "mail.test.multi.company.with.activity", simpleId, true, true],
        [true, "Record, all rights", "mail.test.multi.company.with.activity.read", simpleId, true, true],
        [false, "Record, no write access", "mail.test.multi.company.with.activity", simpleId, true],
        [true, "Record, read access but model accept post with read only access",
            "mail.test.multi.company.with.activity.read", simpleMcId, true],
        [false, "Record, no rights", "mail.test.multi.company.with.activity", simpleId],
        [false, "Record, no rights", "mail.test.multi.company.with.activity.read", simpleMcId],
        // Note that rights have no impact on send button for draft record (chatter.isTemporary=true)
        [true, "Draft record", "mail.test.multi.company.with.activity"],
        [true, "Draft record", "mail.test.multi.company.with.activity.read"],
    ];

    for (const [enabled, description, model, resId, read = false, write = false] of params) {
        await assertChatterButton("Activities", enabled, description, model, resId, read, write);
    }
});

QUnit.test(
    "opened attachment box should remain open after adding a new attachment",
    async (assert) => {
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
        const views = {
            "mail.test.simple.main.attachment,false,form": `
            <form string="Test document">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <div class="oe_chatter">
                    <field name="message_ids"  options="{'post_refresh': 'always'}"/>
                </div>
            </form>`,
        };
        patchUiSize({ size: SIZES.XXL });
        const { openFormView } = await start({
            async mockRPC(route, args) {
                if (String(route).includes("/mail/thread/data")) {
                    await new Promise((resolve) => setTimeout(resolve, 1)); // need extra time for useEffect
                }
            },
            serverData: { views },
        });
        await openFormView("mail.test.simple.main.attachment", recordId);
        await contains(".o_attachment_preview");
        await click("button", { text: "Send message" });
        await inputFiles(".o-mail-Composer-coreMain .o_input_file", [
            await createFile({ name: "testing.jpeg", contentType: "image/jpeg" }),
        ]);
        await click(".o-mail-Composer-send:enabled");
        await click(".o-mail-Chatter-attachFiles");
        await contains(".o-mail-AttachmentBox");
        await click("button", { text: "Send message" });
        await insertText(".o-mail-Composer-input", "test");
        await click(".o-mail-Composer-send:enabled");
        await contains(".o-mail-AttachmentBox .o-mail-AttachmentImage", { count: 2 });
    }
);
