/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("chatter");

QUnit.test("Send message button activation (access rights dependent)", async function (assert) {
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
        await openView({
            res_id: resId,
            res_model: model,
            views: [[false, "form"]],
        });
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
