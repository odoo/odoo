/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { Command } from "@mail/../tests/helpers/command";
import { start } from "@mail/../tests/helpers/test_utils";

import { url } from "@web/core/utils/urls";
import { contains } from "@web/../tests/utils";

const { DateTime } = luxon;

QUnit.module("thread (patch)");

QUnit.test("Rendering of visitor banner", async () => {
    const pyEnv = await startServer();
    const countryId = pyEnv["res.country"].create({ code: "BE" });
    const visitorId = pyEnv["website.visitor"].create({
        country_id: countryId,
        history: "Home → Contact",
        is_connected: true,
        lang_name: "English",
        website_name: "General website",
    });
    pyEnv["website.visitor"].write([visitorId], {
        display_name: `Visitor #${visitorId}`,
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor 11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: `Visitor #${visitorId}`,
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: visitorId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains("img.o-website_livechat-VisitorBanner-avatar");
    const guest = pyEnv["mail.guest"].searchRead([["id", "=", guestId]])[0];
    await contains(
        `img.o-website_livechat-VisitorBanner-avatar[data-src='${url(
            `/web/image/mail.guest/${guestId}/avatar_128?unique=${
                DateTime.fromSQL(guest.write_date).ts
            }`
        )}']`
    );
    await contains(".o-website_livechat-VisitorBanner .o-mail-ImStatus");
    await contains(".o_country_flag[data-src='/base/static/img/country_flags/be.png']");
    await contains(".o-website_livechat-VisitorBanner span", { text: `Visitor #${visitorId}` });
    await contains("span", { text: "English" });
    await contains("span > span", { text: "General website" });
    await contains("span", { text: "Home → Contact" });
});

QUnit.test("Livechat with non-logged visitor should show visitor banner", async () => {
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
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #11",
        channel_member_ids: [
            [0, 0, { partner_id: pyEnv.currentPartnerId }],
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: pyEnv.currentPartnerId,
        livechat_visitor_id: visitorId,
    });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-website_livechat-VisitorBanner");
});

QUnit.test("Livechat with logged visitor should show visitor banner", async () => {
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
    await contains(".o-website_livechat-VisitorBanner");
    await contains(".o-website_livechat-VisitorBanner", { text: "Partner Visitor" });
});

QUnit.test("Livechat without visitor should not show visitor banner", async () => {
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
    await contains(".o-mail-Thread");
    await contains(".o-website_livechat-VisitorBanner", { count: 0 });
});

QUnit.test("Non-livechat channel should not show visitor banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const { openDiscuss } = await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains(".o-website_livechat-VisitorBanner", { count: 0 });
});
