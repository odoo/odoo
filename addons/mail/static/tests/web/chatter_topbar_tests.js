/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { DELAY_FOR_SPINNER } from "@mail/core/web/chatter";

import { makeDeferred } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("chatter topbar");

QUnit.test("base rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Chatter-topbar");
    await contains("button", { text: "Send message" });
    await contains("button", { text: "Log note" });
    await contains("button", { text: "Activities" });
    await contains("button[aria-label='Attach files']");
    await contains(".o-mail-Followers");
});

QUnit.test("rendering with multiple partner followers", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3] = pyEnv["res.partner"].create([
        { name: "Eden Hazard" },
        { name: "Jean Michang" },
        { message_follower_ids: [1, 2] },
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
    const { openView } = await start();
    openView({
        res_id: partnerId_3,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains(".o-mail-Followers");
    await contains(".o-mail-Followers-button");
    await click(".o-mail-Followers-button");
    await contains(".o-mail-Followers-dropdown");
    await contains(".o-mail-Follower", { count: 2 });
    await contains(":nth-child(1 of .o-mail-Follower)", { text: "Jean Michang" });
    await contains(":nth-child(2 of .o-mail-Follower)", { text: "Eden Hazard" });
});

QUnit.test("log note toggling", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button:not(.active)", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });

    await click("button", { text: "Log note" });
    await contains("button.active", { text: "Log note" });
    await contains(".o-mail-Composer .o-mail-Composer-input[placeholder='Log an internal note…']");

    await click("button", { text: "Log note" });
    await contains("button:not(.active)", { text: "Log note" });
    await contains(".o-mail-Composer", { count: 0 });
});

QUnit.test("send message toggling", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button:not(.active)", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });

    await click("button", { text: "Send message" });
    await contains("button.active", { text: "Send message" });
    await contains(".o-mail-Composer-input[placeholder='Send a message to followers…']");

    await click("button", { text: "Send message" });
    await contains("button:not(.active)", { text: "Send message" });
    await contains(".o-mail-Composer", { count: 0 });
});

QUnit.test("log note/send message switching", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
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

QUnit.test("attachment counter without attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button[aria-label='Attach files']");
    await contains("button[aria-label='Attach files']", { count: 0, text: "0" });
});

QUnit.test("attachment counter with attachments", async () => {
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
    const { openView } = await start();
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button[aria-label='Attach files']", { text: "2" });
});

QUnit.test("attachment counter while loading attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { advanceTime, openView } = await start({
        hasTimeControl: true,
        async mockRPC(route) {
            if (route.includes("/mail/thread/data")) {
                await makeDeferred(); // simulate long loading
            }
        },
    });
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button[aria-label='Attach files']");
    await advanceTime(DELAY_FOR_SPINNER);
    await contains("button[aria-label='Attach files'] .fa-spin");
    await contains("button[aria-label='Attach files']", { count: 0, text: "0" });
});

QUnit.test("attachment counter transition when attachments become loaded", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const deferred = makeDeferred();
    const { advanceTime, openView } = await start({
        hasTimeControl: true,
        async mockRPC(route) {
            if (route.includes("/mail/thread/data")) {
                await deferred;
            }
        },
    });
    openView({
        res_id: partnerId,
        res_model: "res.partner",
        views: [[false, "form"]],
    });
    await contains("button[aria-label='Attach files']");
    await advanceTime(DELAY_FOR_SPINNER);
    await contains("button[aria-label='Attach files'] .fa-spin");
    deferred.resolve();
    await contains("button[aria-label='Attach files'] .fa-spin", { count: 0 });
});

QUnit.test(
    "attachment icon open directly the file uploader if there is no attachment yet",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        const { openView } = await start();
        openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        await contains(".o-mail-Chatter-fileUploader");
        await contains(".o-mail-AttachmentBox", { count: 0 });
    }
);

QUnit.test(
    "attachment icon open the attachment box when there is at least 1 attachment",
    async () => {
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
        const { openView } = await start();
        openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });
        await contains("button[aria-label='Attach files']");
        await contains(".o-mail-AttachmentBox", { count: 0 });
        await contains(".o-mail-Chatter-fileUploader", { count: 0 });
        await click("button[aria-label='Attach files']");
        await contains(".o-mail-AttachmentBox");
        await contains(".o-mail-Chatter-fileUploader");
    }
);

QUnit.test("composer state conserved when clicking on another topbar button", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const { openFormView } = await start();
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
