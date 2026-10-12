import {
    click,
    defineMailModels,
    insertText,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD } from "@mail/chatter/web/scheduled_message";
import { mockService, onRpc } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { getOrigin } from "@web/core/utils/urls";
import { MailComposerAttachmentSelector } from "@mail/core/web/mail_composer_attachment_selector";

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { advanceTime, mockDate } from "@odoo/hoot-mock";
import { manuallyDispatchProgrammaticEvent, queryAll, waitFor, waitForNone } from "@odoo/hoot-dom";

beforeEach(() => mockDate("2024-10-20 10:00:00"));
describe.current.tags("desktop");
defineMailModels();

test("Scheduled messages basic layout", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const scheduled_date = "2024-10-20 14:00:00";
    pyEnv["mail.scheduled.message"].create({
        subject: "Greetings",
        body: "<p>Hello There</p>",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date,
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-ScheduledMessagesList:count(1)");
    await waitFor(".o-mail-Scheduled-Message:count(1)");
    await waitFor(".o-mail-Message-author:text('Mitchell Admin'):count(1)");
    const partner = pyEnv["res.partner"].search_read([["id", "=", partnerId]])[0];
    await waitFor(
        `.o-mail-Message-avatarContainer img.cursor-pointer[data-src='${getOrigin()}/web/image/res.partner/${partnerId}/avatar_128?unique=${
            deserializeDateTime(partner.write_date).ts
        }']:count(1)`
    );
    await waitFor(
        `.o-mail-Message-date[title='${deserializeDateTime(scheduled_date).toLocaleString(
            luxon.DateTime.DATETIME_SHORT
        )}']:text('in 3 hours'):count(1)` // 3 hours because luxon toRelative rounds down
    );
    await waitFor(".o-mail-Message-body em:text('Subject: Greetings'):count(1)");
    await waitFor(".o-mail-Message-body p:text('Hello There'):count(1)");
    await waitFor(".o-mail-Message-bubble.bg-success-light:count(1)");
    await waitFor(".o-mail-Scheduled-Message-buttons [data-icon='edit']:count(1)");
    await waitFor(".o-mail-Scheduled-Message-buttons [data-icon='close']:count(1)");
    await click(".o-mail-ScheduledMessagesList > .cursor-pointer");
    await waitForNone(".o-mail-Scheduled-Message");
    await waitFor(
        ".o-mail-ScheduledMessagesList [data-icon='arrow_right'] + span:text('1'):count(1)"
    );
});

test("Scheduled messages are ordered by scheduled date", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    pyEnv["mail.scheduled.message"].create([
        {
            body: "<p>Scheduled Message 1</p>",
            model: "res.partner",
            res_id: partnerId,
            scheduled_date: "2024-10-20 14:00:00",
        },
        {
            body: "<p>Scheduled Message 2</p>",
            model: "res.partner",
            res_id: partnerId,
            scheduled_date: "2024-10-20 12:00:00",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Scheduled-Message:count(2)");
    await waitFor(
        ".o-mail-Scheduled-Message:first-child .o-mail-Message-body p:text('Scheduled Message 2'):count(1)"
    );
    await waitFor(
        ".o-mail-Scheduled-Message:last-child .o-mail-Message-body p:text('Scheduled Message 1'):count(1)"
    );
});

test("Message scheduled by another user can't be edited but can be canceled", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    pyEnv["mail.scheduled.message"].create({
        body: "Hello I'm Mitchell",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    await start({ authenticateAs: false });
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Message-author:text('Mitchell Admin'):count(1)");
    await waitFor(".o-mail-Message-bubble.bg-info-light:count(1)");
    await waitForNone(".o-mail-Scheduled-Message-buttons:text('Edit')");
    await waitFor(".o-mail-Scheduled-Message-buttons:text('Cancel'):count(1)");
});

test("Message scheduled by another user can be edited by admin", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Henri Papier" });
    pyEnv["mail.scheduled.message"].create({
        author_id: partnerId,
        body: "Hello Mitchell",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Message-author:text('Henri Papier'):count(1)");
    await waitFor(".o-mail-Scheduled-Message-buttons:has(:text('Edit')):count(1)");
    await waitFor(".o-mail-Scheduled-Message-buttons:has(:text('Cancel')):count(1)");
});

test("avatar card from author should be opened after clicking on their name or avatar", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({
        name: "Demo",
        email: "demo@example.com",
        phone: "+5646548",
    });
    pyEnv["res.users"].create({
        partner_id: partnerId,
        name: "Demo",
    });
    pyEnv["mail.scheduled.message"].create({
        author_id: partnerId,
        body: "Hello",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Scheduled-Message .o-mail-Message-author:text('Demo')");
    await waitFor(".o-mail-avatar-card-name:text('Demo'):count(1)");
    await waitFor(".o_card_user_infos > a:text('demo@example.com'):count(1)");
    await waitFor(".o_card_user_infos > a:text('+5646548'):count(1)");
    await click(".o-mail-Message-date");
    await waitForNone(".o_card_user_infos");
    await click(".o-mail-Message-avatar");
    await waitFor(".o-mail-avatar-card-name:text('Demo'):count(1)");
});

test("Read more of a scheduled message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    pyEnv["mail.scheduled.message"].create({
        body: "<p>" + "a".repeat(SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD + 1) + "</p>",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(
        ".o-mail-Message-body p:text('" +
            "a".repeat(SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD) +
            "...'):count(1)"
    );
    await click(".o-mail-Message-body button:text('Read More')");
    await waitFor(
        ".o-mail-Message-body p:text('" +
            "a".repeat(SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD + 1) +
            "'):count(1)"
    );
    await click(".o-mail-Message-body button:text('Read Less')");
    await waitFor(
        ".o-mail-Message-body p:text('" +
            "a".repeat(SCHEDULED_MESSAGE_TRUNCATE_THRESHOLD) +
            "...'):count(1)"
    );
    await waitFor(".o-mail-Message-body button:text('Read More'):count(1)");
});

test("Send a scheduled message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const scheduledMessageId = pyEnv["mail.scheduled.message"].create({
        body: "Test Body",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    onRpc("mail.scheduled.message", "post_message", ({ args }) => {
        expect(args).toEqual([scheduledMessageId]);
        pyEnv["mail.message"].create({
            body: "Test Body",
            model: "res.partner",
            res_id: partnerId,
        });
        pyEnv["mail.scheduled.message"].unlink(scheduledMessageId);
        return true;
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Scheduled-Message:count(1)");
    await waitForNone(".o-mail-Message");
    await click(".o-mail-Scheduled-Message-buttons .btn:text('Send Now')");
    await waitForNone(".o-mail-Scheduled-Message");
    await waitFor(".o-mail-Message .o-mail-Message-body:text('Test Body'):count(1)");
});

test("Edit a scheduled message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const scheduledMessageId = pyEnv["mail.scheduled.message"].create({
        subject: "Test Subject",
        body: "Test Body",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    onRpc("mail.scheduled.message", "open_edit_form", ({ args }) => {
        expect(args).toEqual([scheduledMessageId]);
        return {
            name: "Edit Scheduled Message",
        };
    });
    mockService("action", {
        doAction(action, { onClose }) {
            if (action.name === "Edit Scheduled Message") {
                pyEnv["mail.scheduled.message"].write(scheduledMessageId, {
                    subject: "Hi there",
                    body: "<p>Rescheduled later</p>",
                    scheduled_date: "2024-10-20 13:00:00",
                });
                return onClose();
            }
            return super.doAction(...arguments);
        },
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Scheduled-Message:count(1)");
    await click(".o-mail-Scheduled-Message-buttons .btn:text('Edit')");
    await waitFor(".o-mail-Message-body em:text('Subject: Hi there'):count(1)");
    await waitFor(".o-mail-Message-body p:text('Rescheduled later'):count(1)");
    await waitFor(".o-mail-Message-date:text('in 2 hours'):count(1)");
});

test("Cancel a scheduled message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const scheduledMessageId = pyEnv["mail.scheduled.message"].create({
        body: "Hello There",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-ScheduledMessagesList:count(1)");
    await click(".o-mail-Scheduled-Message-buttons .btn:text('Cancel')");
    await click(".modal-footer .btn-primary");
    await waitForNone(".o-mail-ScheduledMessagesList");
    expect(pyEnv["mail.scheduled.message"].browse(scheduledMessageId)).toEqual([]);
});

test("Scheduling a message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    mockService("action", {
        doAction(action, { onClose }) {
            if (action.name === "Compose Email") {
                pyEnv["mail.scheduled.message"].create({
                    body: "New scheduled message",
                    model: action.context.default_model,
                    res_id: action.context.default_res_ids[0],
                    scheduled_date: "2024-10-20 13:00:00",
                });
                return onClose(undefined);
            }
            return super.doAction(...arguments);
        },
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Chatter:count(1)");
    await click(".o-mail-Chatter-sendMessage");
    await click(".o-mail-Composer button[title='Open Full Composer']");
    await waitFor(".o-mail-Scheduled-Message:count(1)");
    await waitFor(".o-mail-Message-body:text('New scheduled message'):count(1)");
});

test("New scheduled message is loaded when sending a message", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Chatter:count(1)");
    await waitForNone(".o-mail-ScheduledMessagesList");
    pyEnv["mail.scheduled.message"].create({
        author_id: pyEnv["res.partner"].create({ name: "Julien Dragoul" }),
        body: "Hello",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 12:00:00",
    });
    await click(".o-mail-Chatter-logNote");
    await waitFor(".o-mail-Composer:count(1)");
    await insertText(".o-mail-Composer-input", "Bloups");
    await click(".o-mail-Composer button:text('Log')");
    await waitFor(".o-mail-ScheduledMessagesList:count(1)");
    await waitFor(".o-mail-Message-author:text('Julien Dragoul'):count(1)");
    await waitFor(".o-mail-Message-body:text('Hello'):count(1)");
});

test("Scheduled messages are updated when switching records", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const partnerId2 = pyEnv["res.partner"].create({});
    pyEnv["mail.scheduled.message"].create([
        {
            body: "Scheduled record 1",
            model: "res.partner",
            res_id: partnerId,
            scheduled_date: "2024-10-20 12:00:00",
        },
        {
            body: "Scheduled record 2",
            model: "res.partner",
            res_id: partnerId2,
            scheduled_date: "2024-10-20 12:00:00",
        },
    ]);
    await start();
    await openFormView("res.partner", partnerId, { resIds: [partnerId, partnerId2] });
    await waitFor(".o-mail-Scheduled-Message:count(1)");
    await waitFor(".o-mail-Message-body:text('Scheduled record 1'):count(1)");
    await click(".o_pager_next");
    await waitFor(".o-mail-Message-body:text('Scheduled record 2'):count(1)");
});

test("Scheduled date is updated when time passes", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    pyEnv["mail.scheduled.message"].create({
        body: "Hello",
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 11:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Message-date:text('in 59 minutes'):count(1)");
    await advanceTime(3600000);
    await waitFor(".o-mail-Message-date:text('now'):count(1)");
});

test("Open avatar card when clicking on partner mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    pyEnv["mail.scheduled.message"].create({
        body: `<a href="${getOrigin()}/odoo#model=res.partner&id=${partnerId}" class="o_mail_redirect" data-oe-model="res.partner" data-oe-id="${partnerId}">@Mitchell Admin</a>`,
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 11:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o_mail_redirect");
    await waitFor(".o_avatar_card:contains('Mitchell Admin'):count(1)");
});

test("Open chat when clicking on channel mention", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const channelId = pyEnv["discuss.channel"].create({ name: "my-channel" });
    pyEnv["mail.scheduled.message"].create({
        body: `<a href="${getOrigin()}/odoo#model=discuss?channel&id=${channelId}" class="o_channel_redirect" data-oe-model="discuss.channel" data-oe-id="${channelId}">#my-channel</a>`,
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 11:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o_channel_redirect");
    await waitFor(".o-mail-ChatWindow .o-mail-Thread:count(1)");
    await waitFor(".o-mail-ChatWindow-displayName:text('my-channel'):count(1)");
});

test("Scheduled message with attachments", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const attachmentIds = pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
        {
            name: "Blu.png",
            mimetype: "image/png",
            res_id: partnerId,
            res_model: "res.partner",
        },
    ]);
    pyEnv["mail.scheduled.message"].create({
        attachment_ids: attachmentIds,
        model: "res.partner",
        res_id: partnerId,
        scheduled_date: "2024-10-20 11:00:00",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await waitFor(".o-mail-Scheduled-Message:count(1)");
    await waitFor(".o-mail-AttachmentList:count(1)");
    await waitFor(".o-mail-Chatter-attachFiles sup:text('2'):count(1)");
    await waitFor(".o-mail-AttachmentCard:count(1)");
    await waitFor(".o-mail-AttachmentImage:count(1)");
});

test("widget mail_composer_attachment_selector: edit attachment of scheduled message", async () => {
    const { promise: isUploaded, resolve: resolveUpload } = Promise.withResolvers();
    patch(MailComposerAttachmentSelector.prototype, {
        async onFileUploaded() {
            await super.onFileUploaded(...arguments);
            resolveUpload();
        },
    });
    const pyEnv = await startServer();
    const partnerId = pyEnv.user.partner_id;
    const scheduled_date = "2024-10-20 14:00:00";
    const attachmentIds = pyEnv["ir.attachment"].create([
        {
            mimetype: "text/plain",
            name: "Blah.txt",
            res_id: partnerId,
            res_model: "res.partner",
        },
    ]);
    const scheduledMessage = pyEnv["mail.scheduled.message"].create({
        subject: "Greetings",
        body: "<p>Hello There</p>",
        attachment_ids: attachmentIds,
        model: "res.partner",
        res_id: partnerId,
        scheduled_date,
    });
    const arch = `
            <form>
                <group>
                    <field name="res_id" widget="many2one_reference_integer"/>
                    <field name="attachment_ids" widget="mail_composer_attachment_list"/>
                    <field name="model"/>
                    <field name="attachment_ids" widget="mail_composer_attachment_selector"/>
                </group>
            </form>
        `;

    await start();
    await openFormView("mail.scheduled.message", scheduledMessage, { arch });
    const fileInputs = queryAll(".o_field_mail_composer_attachment_selector input");
    const textFile = new File(["hello, world"], "text.txt", { type: "text/plain" });

    // redefine 'files' so we can put mock data in through js
    fileInputs.forEach((input) =>
        Object.defineProperty(input, "files", {
            value: [textFile],
        })
    );
    fileInputs.forEach((input) => {
        manuallyDispatchProgrammaticEvent(input, "change");
    });
    await isUploaded;
    await waitFor("[name='attachment_ids'] a:text('text.txt'):count(1)");
});
