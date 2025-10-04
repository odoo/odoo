/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";
import { triggerEvent } from "@web/../tests/helpers/utils";

QUnit.module("messaging menu (patch)");

QUnit.test("rating value displayed on the preview", async (assert) => {
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
    await triggerEvent(document.body, ".o_menu_systray i[aria-label='Messages']", "click");
    assert.containsOnce($, ".o-mail-NotificationItem-text:contains(Rating:)");
    assert.containsOnce($, ".o-rating-preview-image[data-alt='top']");
    assert.containsOnce(
        $,
        ".o-rating-preview-image[data-src='/rating/static/src/img/rating_5.png']"
    );
});

QUnit.test("rating value displayed on the needaction preview", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    const ratingId = pyEnv["mail.test.rating"].create({ name: "Test rating" });
    const messageId = pyEnv["mail.message"].create({
        model: "mail.test.rating",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: ratingId,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: messageId,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
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
    await triggerEvent(document.body, ".o_menu_systray i[aria-label='Messages']", "click");
    assert.containsOnce($, ".o-mail-NotificationItem-text:contains(Rating:)");
    assert.containsOnce($, ".o-rating-preview-image[data-alt='top']");
    assert.containsOnce(
        $,
        ".o-rating-preview-image[data-src='/rating/static/src/img/rating_5.png']"
    );
});
