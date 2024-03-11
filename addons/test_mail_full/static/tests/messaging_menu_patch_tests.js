/* @odoo-module */

import { serverState, startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { click, contains } from "@web/../tests/utils";

QUnit.module("messaging menu (patch)");

QUnit.test("rating value displayed on the preview", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const channelId = pyEnv["discuss.channel"].create({});
    const messageId = pyEnv["mail.message"].create([
        { author_id: partnerId, body: "non-empty", model: "discuss.channel", res_id: channelId },
    ]);
    pyEnv["rating.rating"].create({
        consumed: true,
        message_id: messageId,
        partner_id: partnerId,
        rating_image_url: "/rating/static/src/img/rating_5.png",
        rating_text: "top",
    });
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", { text: "Rating:" });
    await contains(".o-rating-preview-image[data-alt='top']");
    await contains(".o-rating-preview-image[data-src='/rating/static/src/img/rating_5.png']");
});

QUnit.test("rating value displayed on the needaction preview", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const ratingId = pyEnv["mail.test.rating"].create({ name: "Test rating" });
    const messageId = pyEnv["mail.message"].create({
        model: "mail.test.rating",
        needaction: true,
        needaction_partner_ids: [serverState.partnerId],
        res_id: ratingId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: serverState.partnerId,
    });
    pyEnv["rating.rating"].create([
        {
            consumed: true,
            message_id: messageId,
            partner_id: partnerId,
            rating_image_url: "/rating/static/src/img/rating_5.png",
            rating_text: "top",
        },
    ]);
    await start();
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(".o-mail-NotificationItem-text", { text: "Rating:" });
    await contains(".o-rating-preview-image[data-alt='top']");
    await contains(".o-rating-preview-image[data-src='/rating/static/src/img/rating_5.png']");
});
