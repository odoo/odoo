/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { getOrigin } from "@web/core/utils/urls";
import { click, contains } from "@web/../tests/utils";

QUnit.module("attachment list");

QUnit.test("simplest layout", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-Message .o-mail-AttachmentList");
    assert.hasAttrValue($(".o-mail-AttachmentCard"), "title", "test.txt");
    await contains(".o-mail-AttachmentCard-image");
    assert.hasClass($(".o-mail-AttachmentCard-image"), "o_image"); // required for mimetype.scss style
    assert.hasAttrValue($(".o-mail-AttachmentCard-image"), "data-mimetype", "text/plain"); // required for mimetype.scss style
    await contains(".o-mail-AttachmentCard-aside button", { count: 2 });
    await contains(".o-mail-AttachmentCard-unlink");
    await contains(".o-mail-AttachmentCard-aside button[title='Download']");
});

QUnit.test("layout with card details and filename and extension", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentCard", { text: "test.txt" });
    await contains(".o-mail-AttachmentCard small", { text: "txt" });
});

QUnit.test(
    "clicking on the delete attachment button multiple times should do the rpc only once",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "channel1",
        });
        const attachmentId = pyEnv["ir.attachment"].create({
            name: "test.txt",
            mimetype: "text/plain",
        });
        pyEnv["mail.message"].create({
            attachment_ids: [attachmentId],
            body: "<p>Test</p>",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start({
            async mockRPC(route, args) {
                if (route === "/mail/attachment/delete") {
                    assert.step("attachment_unlink");
                }
            },
        });
        openDiscuss(channelId);
        await click(".o-mail-AttachmentCard-unlink");
        await click(".modal-footer .btn-primary");
        await click(".modal-footer .btn-primary");
        await click(".modal-footer .btn-primary");
        await contains(".o-mail-AttachmentCard-unlink", { count: 0 });
        assert.verifySteps(["attachment_unlink"], "The unlink method must be called once");
    }
);

QUnit.test("view attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.png",
        mimetype: "image/png",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentImage img");
    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer");
});

QUnit.test("close attachment viewer", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.png",
        mimetype: "image/png",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentImage img");

    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer");

    await click(".o-FileViewer div[aria-label='Close']");
    await contains(".o-FileViewer", { count: 0 });
});

QUnit.test(
    "[technical] does not crash when the viewer is closed before image load",
    async (assert) => {
        /**
         * When images are displayed using "src" attribute for the 1st time, it fetches the resource.
         * In this case, images are actually displayed (fully fetched and rendered on screen) when
         * "<image>" intercepts "load" event.
         *
         * Current code needs to be aware of load state of image, to display spinner when loading
         * and actual image when loaded. This test asserts no crash from mishandling image becoming
         * loaded from being viewed for 1st time, but viewer being closed while image is loading.
         */
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "channel1",
        });
        const attachmentId = pyEnv["ir.attachment"].create({
            name: "test.png",
            mimetype: "image/png",
        });
        pyEnv["mail.message"].create({
            attachment_ids: [attachmentId],
            body: "<p>Test</p>",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await click(".o-mail-AttachmentImage");
        await contains(".o-FileViewer-viewImage");
        await click(".o-FileViewer div[aria-label='Close']");
        // Simulate image becoming loaded.
        let successfulLoad;
        try {
            document
                .querySelector(".o-FileViewer-viewImage")
                .dispatchEvent(new Event("load", { bubbles: true }));
            successfulLoad = true;
        } catch {
            successfulLoad = false;
        } finally {
            assert.ok(successfulLoad);
        }
    }
);

QUnit.test("plain text file is viewable", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.txt",
        mimetype: "text/plain",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentCard.o-viewable");
});

QUnit.test("HTML file is viewable", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.html",
        mimetype: "text/html",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentCard.o-viewable");
});

QUnit.test("ODT file is not viewable", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.odt",
        mimetype: "application/vnd.oasis.opendocument.text",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentCard:not(.o-viewable)");
});

QUnit.test("DOCX file is not viewable", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.docx",
        mimetype: "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(".o-mail-AttachmentCard:not(.o-viewable)");
});

QUnit.test(
    "should not view attachment from click on non-viewable attachment in list containing a viewable attachment",
    async () => {
        const pyEnv = await startServer();
        const channelId = pyEnv["discuss.channel"].create({
            channel_type: "channel",
            name: "channel1",
        });
        const [attachmentId_1, attachmentId_2] = pyEnv["ir.attachment"].create([
            {
                name: "test.png",
                mimetype: "image/png",
            },
            {
                name: "test.odt",
                mimetype: "application/vnd.oasis.opendocument.text",
            },
        ]);
        pyEnv["mail.message"].create({
            attachment_ids: [attachmentId_1, attachmentId_2],
            body: "<p>Test</p>",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start();
        openDiscuss(channelId);
        await contains(".o-mail-AttachmentImage[title='test.png'] img.o-viewable");
        await contains(".o-mail-AttachmentCard:not(.o-viewable)", { text: "test.odt" });
        await click(".o-mail-AttachmentCard", { text: "test.odt" });
        // weak test, no guarantee that we waited long enough for the potential file viewer to show
        await contains(".o-FileViewer", { count: 0 });
        await click(".o-mail-AttachmentImage[title='test.png']");
        await contains(".o-FileViewer");
    }
);

QUnit.test("img file has proper src in discuss.channel", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.png",
        mimetype: "image/png",
        res_id: channelId,
        res_model: "discuss.channel",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    openDiscuss(channelId);
    await contains(
        `.o-mail-AttachmentImage[title='test.png'] img[data-src='${getOrigin()}/discuss/channel/${channelId}/image/${attachmentId}?filename=test.png&width=1920&height=300']`
    );
});
