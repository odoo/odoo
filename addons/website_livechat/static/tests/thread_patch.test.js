import {
    click,
    contains,
    editInput,
    openDiscuss,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { defineWebsiteLivechatModels } from "./website_livechat_test_helpers";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { url } from "@web/core/utils/urls";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { describe, test } from "@odoo/hoot";
import { mockTimeZone } from "@odoo/hoot-mock";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("Rendering of visitor banner", async () => {
    mockTimeZone(11);
    const pyEnv = await startServer();
    const country_id = pyEnv["res.country"].create({ code: "BE" });
    const lang_id = pyEnv["res.lang"].create({ name: "English" });
    const website_id = pyEnv["website"].create({ name: "General website" });
    const visitor_history = [
        ["Home", "2025-07-16 10:00:20"],
        ["Contact", "2025-07-16 10:20:20"],
    ];
    const visitorId = pyEnv["website.visitor"].create({
        country_id,
        history_data: JSON.stringify(visitor_history),
        is_connected: true,
        lang_id,
        website_id,
    });
    pyEnv["website.visitor"].write([visitorId], {
        display_name: `Visitor #${visitorId}`,
    });
    const guestId = pyEnv["mail.guest"].create({ name: `Visitor #${visitorId}` });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: `Visitor #${visitorId}`,
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    await contains("img.o-website_livechat-VisitorBanner-avatar");
    const [guest] = pyEnv["mail.guest"].search_read([["id", "=", guestId]]);
    await contains(
        `img.o-website_livechat-VisitorBanner-avatar[data-src='${url(
            `/web/image/mail.guest/${guestId}/avatar_128?unique=${
                deserializeDateTime(guest.write_date).ts
            }`
        )}']`
    );
    await contains(".o-website_livechat-VisitorBanner .o-mail-ImStatus");
    await contains(".o_country_flag[data-src='/base/static/img/country_flags/be.png']");
    await contains(".o-website_livechat-VisitorBanner span", { text: `Visitor #${visitorId}` });
    await contains("span", { text: "English" });
    await contains("span > span", { text: "General website" });
    await contains("span", { text: "Home (21:00) → Contact (21:20)" });
});

test("Livechat with non-logged visitor should show visitor banner", async () => {
    mockTimeZone(11);
    const pyEnv = await startServer();
    const country_id = pyEnv["res.country"].create({ code: "BE" });
    const lang_id = pyEnv["res.lang"].create({ name: "English" });
    const website_id = pyEnv["website"].create({ name: "General website" });
    const visitorId = pyEnv["website.visitor"].create({
        country_id,
        display_name: "Visitor #11",
        history_data: JSON.stringify([
            ["Home", "2025-07-16 10:00:20"],
            ["Contact", "2025-07-16 10:20:20"],
        ]),
        is_connected: true,
        lang_id,
        website_id,
    });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #11" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-website_livechat-VisitorBanner span", {
        text: "Home (21:00) → Contact (21:20)",
    });
});

test("Livechat with logged visitor should show visitor banner", async () => {
    mockTimeZone(11);
    const pyEnv = await startServer();
    const country_id = pyEnv["res.country"].create({ code: "BE" });
    const lang_id = pyEnv["res.lang"].create({ name: "English" });
    const website_id = pyEnv["website"].create({ name: "General website" });
    const partner_id = pyEnv["res.partner"].create({ name: "Partner Visitor" });
    const visitorId = pyEnv["website.visitor"].create({
        country_id,
        display_name: "Visitor #11",
        history_data: JSON.stringify([
            ["Home", "2025-07-16 10:00:20"],
            ["Contact", "2025-07-16 10:20:20"],
        ]),
        is_connected: true,
        lang_id,
        partner_id,
        website_id,
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_visitor_id: visitorId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-website_livechat-VisitorBanner");
    await contains(".o-website_livechat-VisitorBanner", { text: "Partner Visitor" });
    await contains(".o-website_livechat-VisitorBanner span", {
        text: "Home (21:00) → Contact (21:20)",
    });
});

test("Livechat without visitor should not show visitor banner", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Harry" });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains(".o-website_livechat-VisitorBanner", { count: 0 });
});

test("Non-livechat channel should not show visitor banner", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread");
    await contains(".o-website_livechat-VisitorBanner", { count: 0 });
});

test("Can create a new record as livechat operator with a custom livechat username", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Harry" });
    pyEnv["res.partner"].write([serverState.partnerId], {
        user_livechat_username: "MitchellOp",
    });
    const channelId = pyEnv["discuss.channel"].create({
        anonymous_name: "Visitor #11",
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ partner_id: partnerId }),
        ],
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
    });
    await start();
    await openDiscuss(channelId); // so that it loads custom livechat username
    await openFormView("res.partner");
    await contains(".o-mail-Message", { text: "Creating a new record..." });
    await editInput(document.body, ".o_field_char input", "test");
    await click(".o_form_button_save");
    await contains(".o-mail-Message", { text: "Creating a new record...", count: 0 });
});
