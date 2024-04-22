import {
    click,
    contains,
    defineMailModels,
    onRpcBefore,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";
import { Deferred, advanceTime } from "@odoo/hoot-mock";
import { onRpc } from "@web/../tests/web_test_helpers";

import { DELAY_FOR_SPINNER } from "@mail/chatter/web_portal/chatter";

describe.current.tags("desktop");
defineMailModels();

test("base rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter-topbar");
    await contains("button", { text: "Send message" });
    await contains("button", { text: "Log note" });
    await contains("button", { text: "Activities" });
    await contains("button[aria-label='Attach files']");
    await contains(".o-mail-Followers");
});

test("rendering with multiple partner followers", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { name: "Eden Hazard" },
        { name: "Jean Michang" },
        {},
    ]);
    pyEnv["mail.followers"].create([
        {
            partner_id: partnerId_2,
            res_id: partnerId_3,
            res_model: "res.partner",
        },
        {
            partner_id: partnerId_1,
            res_id: partnerId_3,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId_3);
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-button");
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown");
    await contains(".o-mail-Follower", { count: 2 });
    await contains(".o-mail-Follower:eq(0)", { text: "Eden Hazard" });
    await contains(".o-mail-Follower:eq(1)", { text: "Jean Michang" });
});

test("log note toggling", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button:not(.active)", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });
    await click("button", { text: "Log note" });
    await contains("button.active", { text: "Log note" });
    await contains(".o-mail-Composer .o-mail-Composer-input[placeholder='Log an internal note…']");
    await click("button", { text: "Log note" });
    await contains("button:not(.active)", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });
});

test("send message toggling", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button:not(.active)", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });
    await click("button", { text: "Send message" });
    await contains("button.active", { text: "Send message" });
    await contains(".o-mail-Composer-input[placeholder='Send a message to followers…']");
    await click("button", { text: "Send message" });
    await contains("button:not(.active)", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });
});

test("log note/send message switching", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button:not(.active)", { text: "Send message" });
    await contains("button:not(.active)", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });
    await click("button", { text: "Send message" });
    await contains("button.active", { text: "Send message" });
    await contains("button:not(.active)", { text: "Log note" });
    await contains(".o-mail-Composer-input[placeholder='Send a message to followers…']");
    await click("button", { text: "Log note" });
    await contains("button:not(.active)", { text: "Send message" });
    await contains("button.active", { text: "Log note" });
    await contains(".o-mail-Composer-input[placeholder='Log an internal note…']");
});

test("attachment counter without attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files']", { count: 0, text: "0" });
});

test("attachment counter with attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
        {
            mimetype: "text/plain",
            name: "Blu.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button[aria-label='Attach files']", { text: "2" });
});

test("attachment counter while loading attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    onRpc("/mail/thread/data", async () => await new Deferred()); // simulate long loading
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button[aria-label='Attach files']");
    await advanceTime(DELAY_FOR_SPINNER);
    await contains("button[aria-label='Attach files'] .fa-spin");
    await contains("button[aria-label='Attach files']", { count: 0, text: "0" });
});

test("attachment counter transition when attachments become loaded", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const deferred = new Deferred();
    onRpcBefore("/mail/thread/data", async () => await deferred);
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button[aria-label='Attach files']");
    await advanceTime(DELAY_FOR_SPINNER);
    await contains("button[aria-label='Attach files'] .fa-spin");
    deferred.resolve();
    await contains("button[aria-label='Attach files'] .fa-spin", { count: 0 });
});

test("attachment icon open directly the file uploader if there is no attachment yet", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter-fileUploader");
    await contains(".o-mail-AttachmentBox", { count: 0 });
});

test("attachment icon open the attachment box when there is at least 1 attachment", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId);
    await contains("button[aria-label='Attach files']");
    await contains(".o-mail-AttachmentBox", { count: 0 });
    await contains(".o-mail-Chatter-fileUploader", { count: 0 });
    await click("button[aria-label='Attach files']");
    await contains(".o-mail-AttachmentBox");
    await contains(".o-mail-Chatter-fileUploader");
});

test("composer state conserved when clicking on another topbar button", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Chatter-topbar");
    await contains("button", { text: "Send message" });
    await contains("button", { text: "Log note" });
    await contains("button[aria-label='Attach files']");
    await click("button", { text: "Log note" });
    await contains("button.active", { text: "Log note" });
    await contains("button:not(.active)", { text: "Send message" });
    await click(".o-mail-Chatter-topbar button[aria-label='Attach files']");
    await contains("button.active", { text: "Log note" });
    await contains("button:not(.active)", { text: "Send message" });
});
