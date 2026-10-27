import {
    click,
    contains,
    defineMailModels,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { queryAttribute } from "@odoo/hoot-dom";
import { onRpc } from "@web/../tests/web_test_helpers";

import { patch } from "@web/core/utils/patch";

describe.current.tags("desktop");
defineMailModels();

test("cloud storage text file is shown in the card and in the viewer", async () => {
    const content = "a".repeat(4096) + "end of file";
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const attachmentId = pyEnv["ir.attachment"].create({
        mimetype: "text/plain",
        name: "notes.txt",
        res_id: partnerId,
        res_model: "res.partner",
        type: "cloud_storage",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [attachmentId],
        body: "<p>Test</p>",
        model: "res.partner",
        res_id: partnerId,
    });
    // the cloud storage can send the whole file even when only the first bytes are asked
    onRpc(`/web/content/${attachmentId}`, () => new Response(content));
    const blobTexts = {};
    patch(URL, {
        createObjectURL(blob) {
            const blobUrl = `blob:${Object.keys(blobTexts).length}`;
            blobTexts[blobUrl] = blob.text();
            return blobUrl;
        },
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-AttachmentCard iframe[data-src^='blob:']");
    const thumbnailUrl = queryAttribute(".o-mail-AttachmentCard iframe", "data-src");
    expect(await blobTexts[thumbnailUrl]).toBe("a".repeat(4096));
    await click(".o-mail-AttachmentCard-info:text('notes.txt')");
    await contains(".o-FileViewer iframe.o-isText[data-src^='blob:']");
    const viewerUrl = queryAttribute(".o-FileViewer iframe.o-isText", "data-src");
    expect(await blobTexts[viewerUrl]).toBe(content);
});
