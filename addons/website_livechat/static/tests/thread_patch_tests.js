/** @odoo-module */

import { start, startServer } from "@mail/../tests/helpers/test_utils";

QUnit.module("thread (patch)");

QUnit.test("Rendering of visitor banner", async (assert) => {
    const pyEnv = await startServer();
    const countryId = pyEnv["res.country"].create({ code: "BE" });
    const visitorId = pyEnv["website.visitor"].create({
        country_id: countryId,
        display_name: "Visitor #11",
        history: "Home → Contact",
        is_connected: true,
        lang_name: "English",
        website_name: "General website",
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Website Visitor 11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: visitorId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, "img.o-website_livechat-VisitorBanner-avatar");
    assert.containsOnce(
        $,
        "img.o-website_livechat-VisitorBanner-avatar[data-src='/mail/static/src/img/smiley/avatar.jpg']"
    );
    assert.containsOnce($, ".o-website_livechat-VisitorBanner .o-mail-ImStatus");
    assert.containsOnce($, ".o_country_flag[data-src='/base/static/img/country_flags/be.png']");
    assert.containsOnce($, "span:contains(Visitor #11)");
    assert.containsOnce($, "span:contains(English)");
    assert.containsOnce($, "span>:contains(General website)");
    assert.containsOnce($, "span:contains(Home → Contact)");
});

QUnit.test("Livechat with non-logged visitor should show visitor banner", async (assert) => {
    const pyEnv = await startServer();
    const countryId = pyEnv["res.country"].create({ code: "BE" });
    const visitorId = pyEnv["website.visitor"].create({
        country_id: countryId,
        display_name: "Visitor #11",
        history: "Home → Contact",
        is_connected: true,
        lang_name: "English",
        website_name: "General website",
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: pyEnv.publicPartnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: visitorId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-website_livechat-VisitorBanner");
});

QUnit.test("Livechat with logged visitor should show visitor banner", async (assert) => {
    const pyEnv = await startServer();
    const resCountryId1 = pyEnv["res.country"].create({ code: "BE" });
    const partnerId = pyEnv["res.partner"].create({ name: "Partner Visitor" });
    const visitorId = pyEnv["website.visitor"].create({
        country_id: resCountryId1,
        display_name: "Visitor #11",
        history: "Home → Contact",
        is_connected: true,
        lang_name: "English",
        partner_id: partnerId,
        website_name: "General website",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: visitorId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-website_livechat-VisitorBanner");
    assert.containsOnce($, ".o-website_livechat-VisitorBanner:contains(Partner Visitor)");
});

QUnit.test("Livechat without visitor should not show visitor banner", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Harry" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            [0, 0, { partner_id: partnerId }],
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Thread");
    assert.containsNone($, ".o-website_livechat-VisitorBanner");
});

QUnit.test("Non-livechat channel should not show visitor banner", async (assert) => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce($, ".o-mail-Thread");
    assert.containsNone($, ".o-website_livechat-VisitorBanner");
});
