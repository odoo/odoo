import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    openFormView,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { methods } from "@web_mobile/js/services/core";

describe.current.tags("desktop");
defineMailModels();

test("'backbutton' event should close attachment viewer", async () => {
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {},
    });

    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({
        channel_type: "channel",
        name: "channel",
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
    });
    await start();
    await openDiscuss();
    await contains("button.active", { text: "Inbox" });
    await click("button", { text: "Channel" });
    await click(".o-mail-NotificationItem", { text: "channel" });
    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer");
    const backButtonEvent = new Event("backbutton");
    document.dispatchEvent(backButtonEvent);
    await contains(".o-FileViewer", { count: 0 });
});

test("[technical] attachment viewer should properly override the back button", async () => {
    // simulate the feature is available on the current device
    // component must and will be destroyed before the overrideBackButton is unpatched
    let overrideBackButton = false;
    patchWithCleanup(methods, {
        overrideBackButton({ enabled }) {
            overrideBackButton = enabled;
        },
    });

    patchUiSize({ size: SIZES.SM });
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "partner 1" });
    const messageAttachmentId = pyEnv["ir.attachment"].create({
        name: "test.png",
        mimetype: "image/png",
    });
    pyEnv["mail.message"].create({
        attachment_ids: [messageAttachmentId],
        body: "<p>Test</p>",
        model: "res.partner",
        res_id: partnerId,
    });
    await start();
    await openFormView("res.partner", partnerId);

    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer");
    expect(overrideBackButton).toBe(true);

    await click(".o-FileViewer div[aria-label='Close']");
    await contains(".o-FileViewer", { count: 0 });
    expect(overrideBackButton).toBe(false);
});
