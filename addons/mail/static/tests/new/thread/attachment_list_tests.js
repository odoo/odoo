/** @odoo-module **/

import { afterNextRender, click, start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture, nextTick } from "@web/../tests/helpers/utils";

let target;

QUnit.module("attachment list", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("simplest layout", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-message .o-mail-attachment-list");
    assert.hasAttrValue($(target).find(".o-mail-attachment-card"), "title", "test.txt");
    assert.containsOnce(target, ".o-mail-attachment-card-image");
    assert.hasClass($(".o-mail-attachment-card-image"), "o_image"); // required for mimetype.scss style
    assert.hasAttrValue($(".o-mail-attachment-card-image"), "data-mimetype", "text/plain"); // required for mimetype.scss style
    assert.containsN(target, ".o-mail-attachment-card-aside button", 2);
    assert.containsOnce(target, ".o-mail-attachment-card-aside-unlink");
    assert.containsOnce(target, ".o-mail-attachment-card-aside button[title='Download']");
});

QUnit.test("layout with card details and filename and extension", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-attachment-card:contains('test.txt')");
    assert.containsOnce(target, ".o-mail-attachment-card small:contains('txt')");
});

QUnit.test(
    "clicking on the delete attachment button multiple times should do the rpc only once",
    async function (assert) {
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
        await click(".o-mail-attachment-card-aside-unlink");
        await afterNextRender(() => {
            document.querySelector(".modal-footer .btn-primary").click();
            document.querySelector(".modal-footer .btn-primary").click();
            document.querySelector(".modal-footer .btn-primary").click();
        });
        assert.verifySteps(["attachment_unlink"], "The unlink method must be called once");
    }
);

QUnit.test("view attachment", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-attachment-image img");
    await click(".o-mail-attachment-image");
    assert.containsOnce(target, ".o-mail-attachment-viewer");
});

QUnit.test("close attachment viewer", async function (assert) {
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
    assert.containsOnce(target, ".o-mail-attachment-image img");

    await click(".o-mail-attachment-image");
    assert.containsOnce(target, ".o-mail-attachment-viewer");

    await click(".o-mail-attachment-viewer div[aria-label='Close']");
    assert.containsNone(target, ".o-mail-attachment-viewer");
});

QUnit.test(
    "[technical] does not crash when the viewer is closed before image load",
    async function (assert) {
        /**
         * When images are displayed using `src` attribute for the 1st time, it fetches the resource.
         * In this case, images are actually displayed (fully fetched and rendered on screen) when
         * `<image>` intercepts `load` event.
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
        await click(".o-mail-attachment-image");
        const imageEl = document.querySelector(".o-mail-attachment-viewer-viewImage");
        await click(".o-mail-attachment-viewer div[aria-label='Close']");
        // Simulate image becoming loaded.
        let successfulLoad;
        try {
            imageEl.dispatchEvent(new Event("load", { bubbles: true }));
            successfulLoad = true;
        } catch {
            successfulLoad = false;
        } finally {
            assert.ok(successfulLoad);
        }
    }
);

QUnit.test("plain text file is viewable", async function (assert) {
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
    assert.hasClass($(target).find(".o-mail-attachment-card"), "o-mail-viewable");
});

QUnit.test("HTML file is viewable", async function (assert) {
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
    assert.hasClass($(target).find(".o-mail-attachment-card"), "o-mail-viewable");
});

QUnit.test("ODT file is not viewable", async function (assert) {
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
    assert.doesNotHaveClass($(target).find(".o-mail-attachment-card"), "o-mail-viewable");
});

QUnit.test("DOCX file is not viewable", async function (assert) {
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
    assert.doesNotHaveClass($(target).find(".o-mail-attachment-card"), "o-mail-viewable");
});

QUnit.test(
    "should not view attachment from click on non-viewable attachment in list containing a viewable attachment",
    async function (assert) {
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
        assert.containsOnce(target, ".o-mail-attachment-image[title='test.png']");
        assert.containsOnce(target, ".o-mail-attachment-card:contains(test.odt)");
        assert.hasClass(
            $(target).find(".o-mail-attachment-image[title='test.png'] img"),
            "o-mail-viewable"
        );
        assert.doesNotHaveClass(
            $(target).find(".o-mail-attachment-card:contains(test.odt)"),
            "o-mail-viewable"
        );

        click(".o-mail-attachment-card:contains(test.odt)").catch(() => {});
        await nextTick();
        assert.containsNone(target, ".o-mail-attachment-viewer");

        await click(".o-mail-attachment-image[title='test.png']");
        assert.containsOnce(target, ".o-mail-attachment-viewer");
    }
);

QUnit.test("img file has proper src in mail.channel", async function (assert) {
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
        $(target)
            .find(".o-mail-attachment-image[title='test.png'] img")
            .data("src")
            .includes(`/mail/channel/${channelId}/image`)
    );
});
