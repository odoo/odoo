import {
    click,
    defineMailModels,
    listenStoreFetch,
    openFormView,
    registerArchs,
    start,
    startServer,
    waitStoreFetch,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor, waitForNone, mockUserAgent } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-mock";

import { DELAY_FOR_SPINNER } from "@mail/chatter/web_portal_project/chatter";

describe.current.tags("desktop");
defineMailModels();

test("base rendering", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Chatter-topbar:count(1)");
    await waitFor("button:text('Send message'):count(1)");
    await waitFor("button:text('Log note'):count(1)");
    await waitFor("button:text('Activity'):count(1)");
    await waitFor("button[aria-label='Attach files']:count(1)");
    await waitFor(".o-mail-Followers:count(1)");
});

async function hasAttachmentPopoutButton(count) {
    if (count) {
        await waitFor(`button i[title='Pop out Attachments']:count(${count})`);
    } else {
        await waitForNone("button i[title='Pop out Attachments']");
    }
}

test("Attachment popout button is shown on desktop", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_id: partnerId,
        res_model: "res.partner",
    });
    registerArchs({
        "res.partner,false,form": `
            <form string="Partner">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <chatter/>
            </form>`,
    });
    listenStoreFetch("mail.thread");
    await start();
    await openFormView("res.partner", partnerId);
    await waitStoreFetch("mail.thread");
    await hasAttachmentPopoutButton(1);
});

test("Attachment popout button is hidden on mobile", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["ir.attachment"].create({
        mimetype: "image/jpeg",
        res_id: partnerId,
        res_model: "res.partner",
    });
    registerArchs({
        "res.partner,false,form": `
            <form string="Partner">
                <sheet>
                    <field name="name"/>
                </sheet>
                <div class="o_attachment_preview"/>
                <chatter/>
            </form>`,
    });
    mockUserAgent("android");
    listenStoreFetch("mail.thread");
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Chatter-topbar");
    await waitStoreFetch("mail.thread");
    await hasAttachmentPopoutButton(0);
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
    await waitFor(".o-mail-Followers:count(1)");
    await waitFor(".o-mail-Followers-button:count(1)");
    await click(".o-mail-Followers-button");
    await waitFor(".o-mail-Followers-dropdown:count(1)");
    await waitFor(".o-mail-Follower:count(2)");
    await waitFor(".o-mail-Follower:eq(0):text('Eden Hazard'):count(1)");
    await waitFor(".o-mail-Follower:eq(1):text('Jean Michang'):count(1)");
});

test("log note toggling", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor("button:not(.active):text('Log note'):count(1)");
    await waitForNone(".o-mail-Composer");
    await click("button:text('Log note')");
    await waitFor("button.active:text('Log note'):count(1)");
    await waitFor(
        ".o-mail-Composer .o-mail-Composer-input[placeholder='Log an internal note…']:count(1)"
    );
    await click("button:text('Log note')");
    await waitFor("button:not(.active):text('Log note'):count(1)");
    await waitForNone(".o-mail-Composer");
});

test("send message toggling", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor("button:not(.active):text('Send message'):count(1)");
    await waitForNone(".o-mail-Composer");
    await click("button:text('Send message')");
    await waitFor("button.active:text('Send message'):count(1)");
    await waitFor(
        ".o-mail-Composer-input[placeholder='Send a message to all followers and selected contacts…']:count(1)"
    );
    await click("button:text('Send message')");
    await waitFor("button:not(.active):text('Send message'):count(1)");
    await waitForNone(".o-mail-Composer");
});

test("log note/send message switching", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor("button:not(.active):text('Send message'):count(1)");
    await waitFor("button:not(.active):text('Log note'):count(1)");
    await waitForNone(".o-mail-Composer");
    await click("button:text('Send message')");
    await waitFor("button.active:text('Send message'):count(1)");
    await waitFor("button:not(.active):text('Log note'):count(1)");
    await waitFor(
        ".o-mail-Composer-input[placeholder='Send a message to all followers and selected contacts…']:count(1)"
    );
    await click("button:text('Log note')");
    await waitFor("button:not(.active):text('Send message'):count(1)");
    await waitFor("button.active:text('Log note'):count(1)");
    await waitFor(".o-mail-Composer-input[placeholder='Log an internal note…']:count(1)");
});

test("attachment counter without attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor("button[aria-label='Attach files']:count(1)");
    await waitForNone("button[aria-label='Attach files']:text('0')");
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
    await waitFor("button[aria-label='Attach files']:text('2'):count(1)");
});

test("attachment counter while loading attachments", async () => {
    const { promise, resolve } = Promise.withResolvers();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    listenStoreFetch("mail.thread", {
        async onRpc() {
            expect.step("before mail.thread");
            await promise;
        },
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor("button[aria-label='Attach files']:count(1)");
    await advanceTime(DELAY_FOR_SPINNER);
    await waitFor("button[aria-label='Attach files'] .oi-spin:count(1)");
    await waitForNone("button[aria-label='Attach files']:text('0')");
    await expect.waitForSteps(["before mail.thread"]);
    resolve();
    await waitStoreFetch("mail.thread");
});

test("attachment counter transition when attachments become loaded", async () => {
    const { promise, resolve } = Promise.withResolvers();
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    listenStoreFetch("mail.thread", {
        async onRpc() {
            expect.step("before mail.thread");
            await promise;
        },
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor("button[aria-label='Attach files']:count(1)");
    await advanceTime(DELAY_FOR_SPINNER);
    await waitFor("button[aria-label='Attach files'] .oi-spin:count(1)");
    await expect.waitForSteps(["before mail.thread"]);
    resolve();
    await waitStoreFetch("mail.thread");
    await waitForNone("button[aria-label='Attach files'] .oi-spin");
});

test("attachment icon open directly the file uploader if there is no attachment yet", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Chatter-fileUploader:count(1)");
    await waitForNone(".o-mail-AttachmentBox");
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
    await waitFor("button[aria-label='Attach files']:count(1)");
    await waitForNone(".o-mail-AttachmentBox");
    await waitForNone(".o-mail-Chatter-fileUploader");
    await click("button[aria-label='Attach files']");
    await waitFor(".o-mail-AttachmentBox:count(1)");
    await waitFor(".o-mail-Chatter-fileUploader:count(1)");
});

test("composer state conserved when clicking on another topbar button", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Chatter-topbar:count(1)");
    await waitFor("button:text('Send message'):count(1)");
    await waitFor("button:text('Log note'):count(1)");
    await waitFor("button[aria-label='Attach files']:count(1)");
    await click("button:text('Log note')");
    await waitFor("button.active:text('Log note'):count(1)");
    await waitFor("button:not(.active):text('Send message'):count(1)");
    await click(".o-mail-Chatter-topbar button[aria-label='Attach files']");
    await waitFor("button.active:text('Log note'):count(1)");
    await waitFor("button:not(.active):text('Send message'):count(1)");
});

test("Send message displays the number of notified followers inside a badge", async () => {
    const pyEnv = await startServer();
    const [partnerId_1, partnerId_2, partnerId_3, partnerId_4] = pyEnv["res.partner"].create([
        { name: "Eden Hazard" },
        { name: "Jean Michang" },
        { name: "Francesco Totti" },
        {},
    ]);
    const [mtCommentId] = pyEnv["mail.message.subtype"].search([
        ["subtype_xmlid", "=", "mail.mt_comment"],
    ]);
    pyEnv["mail.followers"].create([
        {
            partner_id: partnerId_2,
            res_id: partnerId_4,
            res_model: "res.partner",
            subtype_ids: [mtCommentId],
        },
        {
            partner_id: partnerId_1,
            res_id: partnerId_4,
            res_model: "res.partner",
            subtype_ids: [mtCommentId],
        },
        {
            partner_id: partnerId_3,
            res_id: partnerId_4,
            res_model: "res.partner",
            subtype_ids: [],
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId_4);
    await click("button:text('Send message')");
    await waitFor(".o-mail-RecipientsInput .badge:text('2 Followers'):count(1)");
});

test("Attach files and Pinned Messages panels are mutually exclusive", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Armstrong" });
    pyEnv["mail.message"].create({
        body: "Pinned message",
        model: "res.partner",
        pinned_at: "2025-01-01 00:00:00",
        res_id: partnerId,
    });
    pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "A.txt",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click("button[title='Attach files']:text('1')");
    await waitFor(".o-mail-AttachmentBox:count(1)");
    await click("button[title='Pinned Messages']");
    await waitFor(".o-mail-pinnedMessages:count(1)");
    await waitForNone(".o-mail-AttachmentBox");
    await click("button[title='Attach files']:text('1')");
    await waitFor(".o-mail-AttachmentBox:count(1)");
    await waitForNone(".o-mail-pinnedMessages");
});
