import {
    click,
    defineMailModels,
    inputFiles,
    onRpcBefore,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test, waitFor, waitForNone } from "@odoo/hoot";
import { mockFetch, mockUserAgent } from "@odoo/hoot-mock";
import { serverState } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";

import { downloadFile } from "@web/core/network/download";
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
    await waitFor(".o-mail-Message .o-mail-AttachmentList:count(1)");
    expect(".o-mail-AttachmentContainer:first").toHaveAttribute("title", "test.txt");
    await waitFor(".o-mail-AttachmentCard-image:count(1)");
    expect(".o-mail-AttachmentCard-image:first").toHaveClass("o_image"); // required for mimetype.scss style
    expect(".o-mail-AttachmentCard-image:first").toHaveAttribute("data-mimetype", "text/plain"); // required for mimetype.scss style
    await click(".o-mail-AttachmentContainer [title='Actions']");
    await waitFor(".dropdown-item:text('Remove'):count(1)");
    await waitFor(".dropdown-item:text('Download'):count(1)");
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
    await waitFor(".o-mail-AttachmentCard-info:text('test.txt'):count(1)");
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
    await waitFor(".o-mail-AttachmentCard:count(2)");
    await waitFor(".o-mail-AttachmentCard:eq(0):text('url.example'):count(1)");
    await waitFor(".o-mail-AttachmentCard:eq(1):text('test.txt'):count(1)");
    await click(".o-mail-AttachmentContainer:eq(0) [title='Actions']");
    await waitFor(".dropdown-item:text('Remove'):count(1)");
    await waitFor(".dropdown-item:text('Open Link'):count(1)");
    await waitForNone(".dropdown-item:text('Download')");
    await click(".o-mail-AttachmentContainer:eq(1) [title='Actions']");
    await waitFor(".dropdown-item:text('Download'):count(1)");
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
    onRpcBefore("/mail/attachment/delete", () => expect.step("attachment_unlink"));
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-AttachmentContainer [title='Actions']");
    await click(".dropdown-item:text('Remove')");
    await click(".modal-footer .btn-primary");
    await click(".modal-footer .btn-primary");
    await click(".modal-footer .btn-primary");
    await waitForNone(".o-mail-AttachmentContainer");
    await expect.waitForSteps(["attachment_unlink"]); // The unlink method must be called once
});

test("clicking on the delete attachment button multiple times in composer should do the rpc only once", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const text = new File(["hello, world"], "text.txt", { type: "text/plain" });
    let resolveDelete;
    const deletePromise = new Promise((resolve) => {
        resolveDelete = resolve;
    });
    onRpcBefore("/mail/attachment/delete", async () => {
        expect.step("attachment_unlink");
        await deletePromise;
    });
    await start();
    await openDiscuss(channelId);
    await inputFiles(".o-mail-Composer .o_input_file", [text]);
    await waitFor(
        ".o-mail-Composer-footer .o-mail-AttachmentList .o-mail-AttachmentContainer:not(.o-isUploading):contains(text.txt):count(1)"
    );
    await click(".o-mail-Composer .o-mail-AttachmentContainer [title='Remove']");
    await click(".o-mail-Composer .o-mail-AttachmentContainer [title='Remove']");
    resolveDelete();
    // Let the pending deletion settle, so any extra rpc has been registered.
    await waitForNone(".o-mail-Composer .o-mail-AttachmentContainer");
    await expect.waitForSteps(["attachment_unlink"]); // The unlink method must be called once
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
    await waitFor(".o-mail-AttachmentImage:count(1)");
    await click(".o-mail-AttachmentImage");
    await waitFor(".o-FileViewer:count(1)");
});

test("triggers GET on download attachment from the file viewer", async () => {
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
    await click(".o-mail-AttachmentImage");
    await waitFor(".o-FileViewer:count(1)");
    mockFetch((input, init) => {
        expect.step(`${init.method} ${new URL(input, getOrigin()).pathname}`);
        return new Blob(["test"], { type: "image/png" });
    });
    await click(".o-FileViewer-header [title='Download']");
    // Attachment routes of discuss channels only allow GET, a POST download
    // would be rejected with "405 Method Not Allowed".
    await expect.waitForSteps([`GET /web/image/${attachmentId}`]);
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
    await click(".o-mail-AttachmentCard-info:text('url.pdf.example')");
    await waitFor(".o-FileViewer:count(1)");
    await waitFor(
        `iframe.o-FileViewer-view[data-src="/web/static/lib/pdfjs/web/viewer.html?file=${encodeURIComponent(
            `${getOrigin()}/web/content/${attachmentId}?access_token=${attachmentId}&filename=url.pdf.example`
        )}#pagemode=none"]:count(1)`
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
    await waitFor(".o-mail-AttachmentImage:count(1)");
    await click(".o-mail-AttachmentImage");
    await waitFor(".o-FileViewer:count(1)");
    await click(".o-FileViewer div[aria-label='Close']");
    await waitForNone(".o-FileViewer");
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
    await waitFor(".o-FileViewer-viewImage:count(1)");
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
    await waitFor(".o-mail-AttachmentContainer.o-viewable:count(1)");
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
    await waitFor(".o-mail-AttachmentContainer.o-viewable:count(1)");
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
    await waitFor(".o-mail-AttachmentContainer:not(.o-viewable):count(1)");
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
    await waitFor(".o-mail-AttachmentContainer:not(.o-viewable):count(1)");
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
    await waitFor(".o-mail-AttachmentContainer[title='test.png'].o-viewable:count(1)");
    await waitFor(".o-mail-AttachmentContainer:not(.o-viewable):has(:text('test.odt')):count(1)");
    await click(".o-mail-AttachmentContainer:has(:text('test.odt'))");
    // weak test, no guarantee that we waited long enough for the potential file viewer to show
    await waitForNone(".o-FileViewer");
    await click(".o-mail-AttachmentContainer[title='test.png']");
    await waitFor(".o-FileViewer:count(1)");
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
    await waitFor(
        `.o-mail-AttachmentContainer[title='test.png'] img[data-src*='${getOrigin()}/web/image/${attachmentId}?access_token=${attachmentId}&filename=test.png']:count(1)`
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
    patch(downloadFile, {
        _download: (data) => {
            expect(data).toBe(
                `${getOrigin()}/web/content/${attachmentId}?access_token=${attachmentId}&filename=test.o&download=true`
            );
        },
    });
    await click(".o-mail-AttachmentContainer [title='Actions']");
    await click(".dropdown-item:text('Download')");
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
    mockUserAgent("android");
    expect(isMobileOS()).toBe(true);
    await click(".o-mail-AttachmentContainer [title='Actions']");
    await waitFor(".dropdown-item:text('Remove'):count(1)");
    await waitFor(".dropdown-item:text('Download'):count(1)");
});

test("view and play audio attachment", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel1",
    });
    const attachmentId = pyEnv["ir.attachment"].create({
        name: "test.ogg",
        mimetype: "audio/ogg",
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
    await waitFor(".o-mail-AttachmentCard:count(1)");
    await click(".o-mail-AttachmentCard");
    await waitFor(".o-FileViewer audio:count(1)");
});

test("attachment inlined in the body is not listed", async () => {
    const pyEnv = await startServer();
    const [inlinedAttachmentId, attachmentId] = pyEnv["ir.attachment"].create([
        { mimetype: "image/png", name: "inlined.png" },
        { mimetype: "image/png", name: "listed.png" },
    ]);
    pyEnv["mail.message"].create({
        attachment_ids: [inlinedAttachmentId, attachmentId],
        body: `<p><img data-attachment-id="${inlinedAttachmentId}"></p>`,
        message_type: "comment",
        model: "res.partner",
        res_id: serverState.partnerId,
    });
    await start();
    await openFormView("res.partner", serverState.partnerId);
    await waitFor(".o-mail-Message .o-mail-AttachmentContainer[title='listed.png']:count(1)");
    await waitFor(".o-mail-Message .o-mail-AttachmentContainer:count(1)");
});
