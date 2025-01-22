import {
    click,
    contains,
    defineMailModels,
    onRpcBefore,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { mockUserAgent } from "@odoo/hoot-mock";
import { asyncStep, patchWithCleanup, waitForSteps } from "@web/../tests/web_test_helpers";

import { download } from "@web/core/network/download";
import { getOrigin } from "@web/core/utils/urls";
import { isMobileOS } from "@web/core/browser/feature_detection";

describe.current.tags("desktop");
defineMailModels();

test("simplest layout", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Message .o-mail-AttachmentList");
    expect(".o-mail-AttachmentContainer:first").toHaveAttribute("title", "test.txt");
    await contains(".o-mail-AttachmentCard-image");
    expect(".o-mail-AttachmentCard-image:first").toHaveClass("o_image"); // required for mimetype.scss style
    expect(".o-mail-AttachmentCard-image:first").toHaveAttribute("data-mimetype", "text/plain"); // required for mimetype.scss style
    await contains(".o-mail-AttachmentButtons button", { count: 2 });
    await contains(".o-mail-Attachment-unlink");
    await contains(".o-mail-AttachmentButtons button[title='Download']");
});

test("layout with card details and filename and extension", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentContainer", { text: "test.txt" });
});

test("link-type attachment should have open button instead of download button", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachment_ids = pyEnv["ir.attachment"].create([
        {
            name: "url.example",
            mimetype: "text/plain",
            type: "url",
            url: "https://www.odoo.com",
        },
        {
            name: "test.txt",
            mimetype: "text/plain",
        },
    ]);
    pyEnv["mail.message"].create({
        attachment_ids,
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentCard", { count: 2 });
    await contains(".o-mail-AttachmentCard:eq(0)", { text: "url.example" });
    await contains(".o-mail-AttachmentCard:eq(1)", { text: "test.txt" });
    await contains(
        ".o-mail-AttachmentContainer:eq(0) .o-mail-AttachmentButtons a[title='Open Link']"
    );
    await contains(
        ".o-mail-AttachmentContainer:eq(0) .o-mail-AttachmentButtons button[title='Download']",
        { count: 0 }
    );
    await contains(
        ".o-mail-AttachmentContainer:eq(1) .o-mail-AttachmentButtons button[title='Download']"
    );
    await contains(`.o-mail-AttachmentButtons a[title='Open Link'][target='_blank']`);
});

test("clicking on the delete attachment button multiple times should do the rpc only once", async () => {
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
    onRpcBefore("/mail/attachment/delete", () => asyncStep("attachment_unlink"));
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Attachment-unlink");
    await click(".modal-footer .btn-primary");
    await click(".modal-footer .btn-primary");
    await click(".modal-footer .btn-primary");
    await contains(".o-mail-Attachment-unlink", { count: 0 });
    await waitForSteps(["attachment_unlink"]); // The unlink method must be called once
});

test("view attachment", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentImage");
    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer");
});

test("can view pdf url", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "url.pdf.example",
        mimetype: "application/pdf",
        type: "url",
        url: "https://pdfobject.com/pdf/sample.pdf",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-AttachmentContainer", { text: "url.pdf.example" });
    await contains(".o-FileViewer");
    await contains(
        `iframe.o-FileViewer-view[data-src="/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            `${getOrigin()}/web/content/${attachmentId}?filename=url.pdf.example`
        )}#pagemode=none"]`
    );
});

test("close attachment viewer", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentImage");
    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer");
    await click(".o-FileViewer div[aria-label='Close']");
    await contains(".o-FileViewer", { count: 0 });
});

test("[technical] does not crash when the viewer is closed before image load", async () => {
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
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer-viewImage");
    await click(".o-FileViewer div[aria-label='Close']");
    // Simulate image becoming loaded.
    expect(() => {
        document
            .querySelector(".o-FileViewer-viewImage")
            .dispatchEvent(new Event("load", { bubbles: true }));
    }).not.toThrow();
});

test("plain text file is viewable", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentContainer.o-viewable");
});

test("HTML file is viewable", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentContainer.o-viewable");
});

test("ODT file is not viewable", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentContainer:not(.o-viewable)");
});

test("DOCX file is not viewable", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentContainer:not(.o-viewable)");
});

test("should not view attachment from click on non-viewable attachment in list containing a viewable attachment", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-AttachmentContainer[title='test.png'].o-viewable");
    await contains(".o-mail-AttachmentContainer:not(.o-viewable)", { text: "test.odt" });
    await click(".o-mail-AttachmentContainer", { text: "test.odt" });
    // weak test, no guarantee that we waited long enough for the potential file viewer to show
    await contains(".o-FileViewer", { count: 0 });
    await click(".o-mail-AttachmentContainer[title='test.png']");
    await contains(".o-FileViewer");
});

test("img file has proper src in discuss.channel", async () => {
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
    await start();
    await openDiscuss(channelId);
    await contains(
        `.o-mail-AttachmentContainer[title='test.png'] img[data-src*='${getOrigin()}/web/image/${attachmentId}?filename=test.png']`
    );
});

test("download url of non-viewable binary file", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.o",
        mimetype: "application/octet-stream",
        type: "binary",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".fa-download");

    patchWithCleanup(download, {
        _download: (options) => {
            expect(options.url).toBe(`${getOrigin()}/web/content/${attachmentId}?filename=test.o&download=true`);
        },
    });
    await click(".fa-download");
});

test("check actions in mobile view", async () => {
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
    await start();
    await openDiscuss(channelId);
    mockUserAgent("Chrome/0.0.0 Android (OdooMobile; Linux; Android 13; Odoo TestSuite)");
    expect(isMobileOS()).toBe(true);
    await click(".o-mail-AttachmentContainer [title='Actions']");
    await contains(".dropdown-item", { text: "Remove" });
    await contains(".dropdown-item", { text: "Download" });
});
