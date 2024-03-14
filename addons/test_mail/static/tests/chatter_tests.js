const test = QUnit.test; // QUnit.test()

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { openFormView, start } from "@mail/../tests/helpers/test_utils";

import { contains } from "@web/../tests/utils";

QUnit.module("chatter");

test("Send message button activation (access rights dependent)", async function (assert) {
    const pyEnv = await startServer();
    const view = `
        <form string="Simple">
            <sheet>
                <field name="name"/>
            </sheet>
            <chatter/>
        </form>`;
    let userAccess = {};
    await start({
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
    const views = {
        "mail.test.simple,false,form": `
            <form string="Records">
                <sheet>
                    <field name="name"/>
                </sheet>
                <chatter/>
            </form>`,
    };
    await start({ serverData: { views } });
    await openFormView("mail.test.simple", recordId);
    await contains(".o-mail-Chatter");
    await contains(".o-mail-Chatter-topbar");
    await contains("button[aria-label='Attach files']");
    await contains("button", { count: 0, text: "Activities" });
    await contains(".o-mail-Followers");
    await contains(".o-mail-Thread");
});
