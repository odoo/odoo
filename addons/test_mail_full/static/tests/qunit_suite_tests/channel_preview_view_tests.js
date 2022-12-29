/** @odoo-module **/

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture, triggerEvent } from "@web/../tests/helpers/utils";

let target;

QUnit.module("channel preview view", {
    async beforeEach() {
        target = getFixture();
    },
});

QUnit.test("rating value displayed on the thread preview", async function (assert) {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({});
    const mailChannelId1 = pyEnv["mail.channel"].create({});
    const mailMessageId1 = pyEnv["mail.message"].create([
        { author_id: resPartnerId1, model: "mail.channel", res_id: mailChannelId1 },
    ]);
    pyEnv["rating.rating"].create({
        consumed: true,
        message_id: mailMessageId1,
        partner_id: resPartnerId1,
        rating_image_url: "/rating/static/src/img/rating_5.png",
        rating_text: "top",
    });
    await start();
    await triggerEvent(target, ".o_menu_systray i[aria-label='Messages']", "click");
    assert.containsOnce(target, ".o-mail-notification-item-inlineText:contains(Rating:)");
    assert.containsOnce(target, ".o-rating-preview-image[data-alt='top']");
    assert.containsOnce(
        target,
        ".o-rating-preview-image[data-src='/rating/static/src/img/rating_5.png']"
    );
});
