/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture, triggerEvent } from "@web/../tests/helpers/utils";

let target;

QUnit.module("thread needaction preview", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("rating value displayed on the thread needaction preview", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailTestRating1 = pyEnv["mail.test.rating"].create({ name: "Test rating" });
    const mailMessageId1 = pyEnv["mail.message"].create({
        model: "mail.test.rating",
        needaction: true,
        needaction_partner_ids: [pyEnv.currentPartnerId],
        res_id: mailTestRating1,
    });
    pyEnv["mail.notification"].create({
        mail_message_id: mailMessageId1,
        notification_status: "sent",
        notification_type: "inbox",
        res_partner_id: pyEnv.currentPartnerId,
    });
    pyEnv["rating.rating"].create([
        {
            consumed: true,
            message_id: mailMessageId1,
            partner_id: resPartnerId1,
            rating_image_url: "/rating/static/src/img/rating_5.png",
            rating_text: "top",
        },
    ]);
    await start();
    await triggerEvent(target, ".o_menu_systray i[aria-label='Messages']", "click");
    assert.containsOnce(target, ".o-mail-notification-item-inlineText:contains(Rating:)");
    assert.containsOnce(target, ".o-rating-preview-image[data-alt='top']");
    assert.containsOnce(
        target,
        ".o-rating-preview-image[data-src='/rating/static/src/img/rating_5.png']"
    );
});
