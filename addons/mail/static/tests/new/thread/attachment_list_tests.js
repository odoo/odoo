/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { nextTick } from "@web/../tests/helpers/utils";

QUnit.module("attachment list");

QUnit.test("simplest layout", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-Message .o-AttachmentList");
    assert.hasAttrValue($(".o-AttachmentCard"), "title", "test.txt");
    assert.containsOnce($, ".o-AttachmentCard-image");
    assert.hasClass($(".o-AttachmentCard-image"), "o_image"); // required for mimetype.scss style
    assert.hasAttrValue($(".o-AttachmentCard-image"), "data-mimetype", "text/plain"); // required for mimetype.scss style
    assert.containsN($, ".o-AttachmentCard-aside button", 2);
    assert.containsOnce($, ".o-AttachmentCard-unlink");
    assert.containsOnce($, ".o-AttachmentCard-aside button[title='Download']");
});

QUnit.test("layout with card details and filename and extension", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-AttachmentCard:contains('test.txt')");
    assert.containsOnce($, ".o-AttachmentCard small:contains('txt')");
});

QUnit.test(
    "clicking on the delete attachment button multiple times should do the rpc only once",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
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
            model: "mail.channel",
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
        await openDiscuss(channelId);
        await click(".o-AttachmentCard-unlink");
        await afterNextRender(() => {
            $(".modal-footer .btn-primary")[0].click();
            $(".modal-footer .btn-primary")[0].click();
            $(".modal-footer .btn-primary")[0].click();
        });
        assert.verifySteps(["attachment_unlink"], "The unlink method must be called once");
    }
);

QUnit.test("view attachment", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-AttachmentImage img");
    await click(".o-AttachmentImage");
    assert.containsOnce($, ".o-AttachmentViewer");
});

QUnit.test("close attachment viewer", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-AttachmentImage img");

    await click(".o-AttachmentImage");
    assert.containsOnce($, ".o-AttachmentViewer");

    await click(".o-AttachmentViewer div[aria-label='Close']");
    assert.containsNone($, ".o-AttachmentViewer");
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
        const channelId = pyEnv["mail.channel"].create({
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
            model: "mail.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        await click(".o-AttachmentImage");
        const image = $(".o-AttachmentViewer-viewImage")[0];
        await click(".o-AttachmentViewer div[aria-label='Close']");
        // Simulate image becoming loaded.
        let successfulLoad;
        try {
            image.dispatchEvent(new Event("load", { bubbles: true }));
            successfulLoad = true;
        } catch {
            successfulLoad = false;
        } finally {
            assert.ok(successfulLoad);
        }
    }
);

QUnit.test("plain text file is viewable", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.hasClass($(".o-AttachmentCard"), "o-viewable");
});

QUnit.test("HTML file is viewable", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.hasClass($(".o-AttachmentCard"), "o-viewable");
});

QUnit.test("ODT file is not viewable", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.doesNotHaveClass($(".o-AttachmentCard"), "o-viewable");
});

QUnit.test("DOCX file is not viewable", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
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
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.doesNotHaveClass($(".o-AttachmentCard"), "o-viewable");
});

QUnit.test(
    "should not view attachment from click on non-viewable attachment in list containing a viewable attachment",
    async (assert) => {
        const pyEnv = await startServer();
        const channelId = pyEnv["mail.channel"].create({
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
            model: "mail.channel",
            res_id: channelId,
            message_type: "comment",
        });
        const { openDiscuss } = await start();
        await openDiscuss(channelId);
        assert.containsOnce($, ".o-AttachmentImage[title='test.png']");
        assert.containsOnce($, ".o-AttachmentCard:contains(test.odt)");
        assert.hasClass($(".o-AttachmentImage[title='test.png'] img"), "o-viewable");
        assert.doesNotHaveClass($(".o-AttachmentCard:contains(test.odt)"), "o-viewable");

        click(".o-AttachmentCard:contains(test.odt)").catch(() => {});
        await nextTick();
        assert.containsNone($, ".o-AttachmentViewer");

        await click(".o-AttachmentImage[title='test.png']");
        assert.containsOnce($, ".o-AttachmentViewer");
    }
);

QUnit.test("img file has proper src in mail.channel", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.png",
        mimetype: "image/png",
        res_id: channelId,
        res_model: "mail.channel",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "mail.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.ok(
        $(".o-AttachmentImage[title='test.png'] img")
            .data("src")
            .includes(`/mail/channel/${channelId}/image`)
    );
});
