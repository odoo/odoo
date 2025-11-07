import {
    click,
    contains,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, press, test } from "@odoo/hoot";
import { Command, serverState } from "@web/../tests/web_test_helpers";
import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("livechat note is loaded when opening the channel info list", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({
        name: "Visitor #20",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        country_id: countryId,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_note: "<p>Initial note<br/>Second line</p>",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-livechat-ChannelInfoList textarea", { value: "Initial note\nSecond line" });
});

test("editing livechat note is synced between tabs", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({
        name: "Visitor #20",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        country_id: countryId,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_note: "<p>Initial note</p>",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: tab1 });
    await openDiscuss(channelId, { target: tab2 });
    await contains(`${tab1.selector} .o-livechat-ChannelInfoList textarea`, {
        value: "Initial note",
    });
    await contains(`${tab2.selector} .o-livechat-ChannelInfoList textarea`, {
        value: "Initial note",
    });
    await insertText(`${tab1.selector} .o-livechat-ChannelInfoList textarea`, "Updated note", {
        replace: true,
    });
    document.querySelector(`${tab1.selector} .o-livechat-ChannelInfoList textarea`).blur(); // Trigger the blur event to save the note
    await contains(`${tab2.selector} .o-livechat-ChannelInfoList textarea`, {
        value: "Updated note",
    }); // Note should be synced with bus
});

test("shows live chat status in discuss sidebar", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({
        name: "Visitor #20",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        country_id: countryId,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_status: "waiting",
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-livechat-ChannelInfoList button.active", { text: "Waiting for customer" });
    await contains(".o-mail-DiscussSidebar-item span[title='Waiting for customer']");
    await click(".o-livechat-ChannelInfoList button", { text: "Looking for help" });
    await contains(".o-livechat-ChannelInfoList button.active", { text: "Looking for help" });
    await contains(".o-mail-DiscussSidebar-item span[title='Looking for help']");
    // live chat status icon also in messaging menu item
    await click(".o_menu_systray i[aria-label='Messages']");
    await contains(
        ".o-mail-MessagingMenu .o-mail-NotificationItem:contains('Visitor #20') [title='Looking for help']"
    );
});

test("editing livechat status is synced between tabs", async () => {
    const pyEnv = await startServer();
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({
        name: "James",
        user_ids: [userId],
    });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({
        name: "Visitor #20",
    });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId }),
            Command.create({ guest_id: guestId }),
        ],
        country_id: countryId,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_status: "in_progress",
    });
    const tab1 = await start({ asTab: true });
    const tab2 = await start({ asTab: true });
    await openDiscuss(channelId, { target: tab1 });
    await openDiscuss(channelId, { target: tab2 });
    await contains(`${tab1.selector} .o-livechat-ChannelInfoList button.active`, {
        text: "In progress",
    });
    await contains(`${tab2.selector} .o-livechat-ChannelInfoList button.active`, {
        text: "In progress",
    });
    await click(`${tab1.selector} .o-livechat-ChannelInfoList button`, {
        text: "Waiting for customer",
    });
    await contains(`${tab1.selector} .o-livechat-ChannelInfoList button.active`, {
        text: "Waiting for customer",
    });
    await contains(`${tab2.selector} .o-livechat-ChannelInfoList button.active`, {
        text: "Waiting for customer",
    }); // Status should be synced with bus
});

test("Manage expertises from channel info list", async () => {
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatManagerId]])
            .map(({ id }) => id),
    });
    const userId = pyEnv["res.users"].create({ name: "James" });
    pyEnv["res.partner"].create({ name: "James", user_ids: [userId] });
    const countryId = pyEnv["res.country"].create({ code: "be", name: "Belgium" });
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor #20" });
    const expertiseIds = pyEnv["im_livechat.expertise"].create([{ name: "pricing" }]);
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({ partner_id: serverState.partnerId, livechat_member_type: "agent" }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        country_id: countryId,
        channel_type: "livechat",
        livechat_operator_id: serverState.partnerId,
        livechat_expertise_ids: expertiseIds,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-livechat-ChannelInfoList .o_tag", { text: "pricing" });
    await insertText(".o-livechat-ExpertiseTagsAutocomplete input", "events");
    await click("a", { text: 'Create "events"' });
    await contains(".o-livechat-ChannelInfoList .o_tag", { text: "events" });
    await click(".o-livechat-ExpertiseTagsAutocomplete input");
    await press("Backspace");
    await contains(".o-livechat-ChannelInfoList .o_tag", { text: "events", count: 0 });
    await press("Backspace");
    await contains(".o-livechat-ChannelInfoList .o_tag", { text: "pricing", count: 0 });
    await contains(".o-livechat-ExpertiseTagsAutocomplete input[placeholder='Add expertise']");
    await click("a", { text: "events" });
    await contains(".o-livechat-ChannelInfoList .o_tag", { text: "events" });
});
