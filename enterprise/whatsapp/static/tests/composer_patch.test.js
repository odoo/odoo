import { Composer } from "@mail/core/common/composer";
import {
    contains,
    dragenterFiles,
    dropFiles,
    inputFiles,
    insertText,
    openDiscuss,
    pasteFiles,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { beforeEach, describe, test } from "@odoo/hoot";
import { serializeDateTime } from "@web/core/l10n/dates";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { defineWhatsAppModels } from "@whatsapp/../tests/whatsapp_test_helpers";

const { DateTime } = luxon;

describe.current.tags("desktop");
defineWhatsAppModels();

beforeEach(() => {
    // Simulate real user interactions
    patchWithCleanup(Composer.prototype, {
        isEventTrusted() {
            return true;
        },
    });
});

test("Allow only single attachment in every message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss(channelId);
    const [file1, file2] = [
        new File(["hello, world"], "text.txt", { type: "text/plain" }),
        new File(["hello, world"], "text2.txt", { type: "text/plain" }),
    ];

    await contains(".o-mail-Composer");
    await contains("button[title='Attach files']");
    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [file1]);
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");
    await contains("button[title='Attach files']:disabled");

    await pasteFiles(".o-mail-Composer-input", [file2]);
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");

    await dragenterFiles(".o-mail-Composer-input", [file2]);
    await dropFiles(".o-Dropzone", [file2]);
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");
});

test("Can not add attachment after copy pasting an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss(channelId);
    const [file1, file2] = [
        new File(["hello, world"], "text.txt", { type: "text/plain" }),
        new File(["hello, world"], "text2.txt", { type: "text/plain" }),
    ];
    await pasteFiles(".o-mail-Composer-input", [file1]);
    await contains("button[title='Attach files']:disabled");
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");

    await pasteFiles(".o-mail-Composer-input", [file2]);
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");

    await dragenterFiles(".o-mail-Composer-input", [file2]);
    await dropFiles(".o-Dropzone", [file2]);
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");
});

test("Can not add attachment after drag dropping an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss(channelId);
    const [file1, file2] = [
        new File(["hello, world"], "text.txt", { type: "text/plain" }),
        new File(["hello, world"], "text2.txt", { type: "text/plain" }),
    ];
    await dragenterFiles(".o-mail-Composer-input", [file1]);
    await dropFiles(".o-Dropzone", [file1]);
    await contains("button[title='Attach files']:disabled");
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");

    await pasteFiles(".o-mail-Composer-input", [file2]);
    await contains(".o-mail-AttachmentCard");
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(text.txt) .fa-check");
});

test("Can not add multiple attachments simultaneously via drag and drop", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss(channelId);
    const [file1, file2, file3] = [
        new File(["hello"], "text1.txt", { type: "text/plain" }),
        new File(["world"], "text2.txt", { type: "text/plain" }),
        new File(["single"], "single.txt", { type: "text/plain" }),
    ];
    await dragenterFiles(".o-mail-Composer-input", [file1, file2]);
    await dropFiles(".o-Dropzone", [file1, file2]);
    await contains(".o_notification", { text: "Only one attachment is allowed for each message" });
    await dragenterFiles(".o-mail-Composer-input", [file3]);
    await dropFiles(".o-Dropzone", [file3]);
    await contains(".o-mail-AttachmentCard", { count: 1 });
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(single.txt) .fa-check");
});

test("Can not add multiple attachments simultaneously via paste", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss(channelId);
    const [file1, file2, file3] = [
        new File(["hello"], "text1.txt", { type: "text/plain" }),
        new File(["world"], "text2.txt", { type: "text/plain" }),
        new File(["single"], "single.txt", { type: "text/plain" }),
    ];
    await pasteFiles(".o-mail-Composer-input", [file1, file2]);
    await contains(".o_notification", { text: "Only one attachment is allowed for each message" });
    await pasteFiles(".o-mail-Composer-input", [file3]);
    await contains(".o-mail-AttachmentCard", { count: 1 });
    await contains(".o-mail-AttachmentCard:not(.o-isUploading):contains(single.txt) .fa-check");
});

test("Disabled composer should be enabled after message from whatsapp user", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        whatsapp_channel_valid_until: serializeDateTime(DateTime.local().minus({ minutes: 1 })),
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-input[readonly]");
    await contains(".o-mail-Composer-send", { count: 0 });
    await contains(".o-mail-Composer-actions", { count: 0 });
    await contains("button[title='Attach files']", { count: 0 });

    // stimulate the notification sent after receiving a message from whatsapp user
    const [channel] = pyEnv["discuss.channel"].search_read([["id", "=", channelId]]);
    pyEnv["bus.bus"]._sendone(
        channel,
        "mail.record/insert",
        new mailDataHelpers.Store(pyEnv["discuss.channel"].browse(channelId), {
            whatsapp_channel_valid_until: DateTime.utc().plus({ days: 1 }).toSQL(),
        }).get_result()
    );
    await contains(".o-mail-Composer-actions");
    await contains("button[title='Attach files']");
    await insertText(".o-mail-Composer-input:not([readonly])", "Hello");
    await contains(".o-mail-Composer-send:enabled");
});

test("Allow channel commands for whatsapp channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await contains(".o-mail-NavigableList-item", { text: "leaveLeave this channel" });
});
