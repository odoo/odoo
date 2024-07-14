/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { Composer } from "@mail/core/common/composer";
import { patchWithCleanup } from "@web/../tests/helpers/utils";
import {
    contains,
    createFile,
    dragenterFiles,
    dropFiles,
    inputFiles,
    insertText,
    pasteFiles,
} from "@web/../tests/utils";

const { DateTime } = luxon;

QUnit.module("composer (patch)", {
    async beforeEach() {
        // Simulate real user interactions
        patchWithCleanup(Composer.prototype, {
            isEventTrusted() {
                return true;
            },
        });
    },
});

QUnit.test("Allow only single attachment in every message", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const [file1, file2] = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text2.txt",
        }),
    ];
    await contains(".o-mail-Composer");
    await contains("button[title='Attach files']");

    await inputFiles(".o-mail-Composer-coreMain .o_input_file", [file1]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });
    await contains("button[title='Attach files']:disabled");

    await pasteFiles(".o-mail-Composer-input", [file2]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });

    await dragenterFiles(".o-mail-Composer-input", [file2]);
    await dropFiles(".o-mail-Dropzone", [file2]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });
});

QUnit.test("Can not add attachment after copy pasting an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const [file1, file2] = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text2.txt",
        }),
    ];
    await pasteFiles(".o-mail-Composer-input", [file1]);
    await contains("button[title='Attach files']:disabled");
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });

    await pasteFiles(".o-mail-Composer-input", [file2]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });

    await dragenterFiles(".o-mail-Composer-input", [file2]);
    await dropFiles(".o-mail-Dropzone", [file2]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });
});

QUnit.test("Can not add attachment after drag dropping an attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    const [file1, file2] = [
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text.txt",
        }),
        await createFile({
            content: "hello, world",
            contentType: "text/plain",
            name: "text2.txt",
        }),
    ];
    await dragenterFiles(".o-mail-Composer-input", [file1]);
    await dropFiles(".o-mail-Dropzone", [file1]);
    await contains("button[title='Attach files']:disabled");
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });

    await pasteFiles(".o-mail-Composer-input", [file2]);
    await contains(".o-mail-AttachmentCard", { text: "text.txt", contains: [".fa-check"] });
});

QUnit.test("Disabled composer should be enabled after message from whatsapp user", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
        whatsapp_channel_valid_until: DateTime.utc().minus({ minutes: 1 }).toSQL(),
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer-actions");
    await contains("button[title='Attach files']");
    await contains(".o-mail-Composer-send");
    await contains(".o-mail-Composer-input[readonly]");

    // stimulate the notification sent after receiving a message from whatsapp user
    const [channel] = pyEnv["discuss.channel"].searchRead([["id", "=", channelId]]);

    pyEnv["bus.bus"]._sendone(channel, "discuss.channel/whatsapp_channel_valid_until_changed", {
        id: channelId,
        whatsapp_channel_valid_until: DateTime.utc().plus({ days: 1 }).toSQL(),
    });
    await contains(".o-mail-Composer-actions");
    await contains("button[title='Attach files']");
    await contains(".o-mail-Composer-send");
    await contains(".o-mail-Composer-input:not([readonly])");
});

QUnit.test("Allow channel commands for whatsapp channels", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        name: "WhatsApp 1",
        channel_type: "whatsapp",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await insertText(".o-mail-Composer-input", "/");
    await contains(".o-mail-NavigableList-item", { text: "leaveLeave this channel" });
});
