import {
    click,
    contains as mailContains,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("activity assign popover simplest layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
        user_id: false,
    });

    onRpc("mail.activity", "write", () => {
        throw new Error("RPC 'write' must not be called on discard");
    });

    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Activity-assign");
    await waitFor(".o-mail-ActivityAssignPopover:count(1)");
    await waitFor(".o-mail-ActivityAssignPopover input[type='text']:count(1)");
    await waitFor(".o-mail-ActivityAssignPopover button[aria-label='Assign']:count(1)");
    await waitFor(".o-mail-ActivityAssignPopover button[aria-label='Discard']:count(1)");
    await click(".o-mail-ActivityAssignPopover button[aria-label='Discard']");
    await waitForNone(".o-mail-ActivityAssignPopover");
});

test("activity assign popover assign user", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        can_write: true,
        res_id: partnerId,
        res_model: "res.partner",
        user_id: false,
    });

    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Activity-assign");
    await insertText(".o-mail-ActivityAssignPopover input[type='text']", "Mitchell");
    await click(".ui-menu-item:text('Mitchell Admin')");
    await click(".o-mail-ActivityAssignPopover button[aria-label='Assign']");
    await waitForNone(".o-mail-ActivityAssignPopover");
    await mailContains(".o-mail-Activity-user", { text: "for Mitchell Admin" });
});
