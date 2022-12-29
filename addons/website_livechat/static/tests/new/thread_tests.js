/** @odoo-module */

import { start, startServer } from "@mail/../tests/helpers/test_utils";
import { getFixture } from "@web/../tests/helpers/utils";

let target;
QUnit.module("thread", {
    beforeEach() {
        target = getFixture();
    },
});

QUnit.test("Rendering of visitor banner", async function (assert) {
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
    const channelId = pyEnv["mail.channel"].create({
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
    assert.containsOnce(target, ".o-mail-visitor-banner-avatar");
    assert.containsOnce(
        target,
        ".o-mail-visitor-banner-avatar[data-src='/mail/static/src/img/smiley/avatar.jpg']"
    );
    assert.containsOnce(target, ".o-mail-visitor-banner-avatar-container .o-mail-im-status");
    assert.containsOnce(
        target,
        ".o_country_flag[data-src='/base/static/img/country_flags/be.png']"
    );
    assert.containsOnce(target, "span:contains(Visitor 11)");
    assert.containsOnce(target, "span:contains(English)");
    assert.containsOnce(target, "span>:contains(General website)");
    assert.containsOnce(target, "span:contains(Home → Contact)");
});

QUnit.test("Livechat with non-logged visitor should show visitor banner", async function (assert) {
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
    const channelId = pyEnv["mail.channel"].create({
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
    assert.containsOnce(target, ".o-mail-visitor-banner");
});

QUnit.test("Livechat with logged visitor should show visitor banner", async function (assert) {
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
    const channelId = pyEnv["mail.channel"].create({
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
    assert.containsOnce(target, ".o-mail-visitor-banner");
});

QUnit.test("Livechat without visitor should not show visitor banner", async function (assert) {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Harry" });
    const channelId = pyEnv["mail.channel"].create({
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
    assert.containsOnce(target, ".o-mail-thread");
    assert.containsNone(target, ".o-mail-visitor-banner");
});

QUnit.test("Non-livechat channel should not show visitor banner", async function (assert) {
    const pyEnv = await startServer();
    const channelId = pyEnv["mail.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    assert.containsOnce(target, ".o-mail-thread");
    assert.containsNone(target, ".o-mail-visitor-banner");
});
