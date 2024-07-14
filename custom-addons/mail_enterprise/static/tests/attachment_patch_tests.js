/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { patchUiSize, SIZES } from "@mail/../tests/helpers/patch_ui_size";
import { start } from "@mail/../tests/helpers/test_utils";

import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { click, contains } from "@web/../tests/utils";

import { methods } from "@web_mobile/js/services/core";

QUnit.module("attachment (patch)");

QUnit.test("'backbutton' event should close attachment viewer", async () => {
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
    const { openDiscuss } = await start();
    await openDiscuss();
    await click("button", { text: "Channel" });
    await click(".o-mail-NotificationItem", { text: "channel" });
    await click(".o-mail-AttachmentImage");
    await contains(".o-FileViewer");
    const backButtonEvent = new Event("backbutton");
    document.dispatchEvent(backButtonEvent);
    await contains(".o-FileViewer", { count: 0 });
});

QUnit.test(
    "[technical] attachment viewer should properly override the back button",
    async (assert) => {
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
        const { openView } = await start();
        await openView({
            res_id: partnerId,
            res_model: "res.partner",
            views: [[false, "form"]],
        });

        await click(".o-mail-AttachmentImage");
        await contains(".o-FileViewer");
        assert.ok(overrideBackButton);

        await click(".o-FileViewer div[aria-label='Close']");
        await contains(".o-FileViewer", { count: 0 });
        assert.notOk(overrideBackButton);
    }
);
