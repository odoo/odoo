import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    mockGetMedia,
    openDiscuss,
    patchUiSize,
    SIZES,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { Settings } from "@mail/core/common/settings_model";
import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { getService, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

beforeEach(() => {
    serverState.serverVersion = [99, 9]; // high version so following upgrades keep good working of feature
});

test("message sound is 'off'", async () => {
    localStorage.setItem("mail.user_setting.message_sound", "false");
    await start();
    getService("action").doAction({
        tag: "mail.discuss_notification_settings_action",
        type: "ir.actions.client",
    });
    await contains("label:has(h5:contains('Message sound')) input:not(:checked)");
    const messageSoundKey = makeRecordFieldLocalId(Settings.localId(), "messageSound");
    expect(localStorage.getItem(messageSoundKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail.user_setting.message_sound")).toBe(null);
});

test("use blur is 'on'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail_user_setting_use_blur", "true");
    patchUiSize({ size: SIZES.SM });
    await start();
    await openDiscuss(channelId);
    // dropdown requires an extra delay before click (because handler is registered in useEffect)
    await contains("[title='Open Actions Menu']");
    await click("[title='Open Actions Menu']");
    await click(".o-dropdown-item", { text: "Call Settings" });
    await contains(".o-discuss-CallSettings");
    await contains(
        ".o-discuss-CallSettings-item:has(label:contains('Blur video background')) input:checked"
    );
    const useBlurKey = makeRecordFieldLocalId(Settings.localId(), "useBlur");
    expect(localStorage.getItem(useBlurKey)).toBe(toRawValue(true));
    expect(localStorage.getItem("mail_user_setting_use_blur")).toBe(null);
});

test("member default open is 'off'", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail.user_setting.no_members_default_open", "true");
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Thread:contains('Welcome to #test')");
    await contains(".o-mail-ActionList-button[title='Members']");
    await contains(".o-mail-ActionList-button[title='Members']:not(.active)");
    const isMemberPanelOpenByDefaultKey = makeRecordFieldLocalId(
        DiscussApp.localId(),
        "isMemberPanelOpenByDefault"
    );
    expect(localStorage.getItem(isMemberPanelOpenByDefaultKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail.user_setting.no_members_default_open")).toBe(null);
    await click(".o-mail-ActionList-button[title='Members']");
    await contains(".o-mail-ActionList-button[title='Members'].active"); // just to validate .active is correct selector
    expect(localStorage.getItem(isMemberPanelOpenByDefaultKey)).toBe(null);
});

test("sidebar compact is 'on'", async () => {
    localStorage.setItem("mail.user_setting.discuss_sidebar_compact", "true");
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebar.o-compact");
    const isSidebarCompact = makeRecordFieldLocalId(DiscussApp.localId(), "isSidebarCompact");
    expect(localStorage.getItem(isSidebarCompact)).toBe(toRawValue(true));
    expect(localStorage.getItem("mail.user_setting.discuss_sidebar_compact")).toBe(null);
});

test("category 'Channels' is folded", async () => {
    localStorage.setItem("discuss_sidebar_category_folded_channels", "true");
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Channels') .oi.oi-chevron-right");
    const channels_is_open = makeRecordFieldLocalId(
        DiscussAppCategory.localId("channels"),
        "is_open"
    );
    expect(localStorage.getItem(channels_is_open)).toBe(toRawValue(false));
    expect(localStorage.getItem("discuss_sidebar_category_folded_channels")).toBe(null);
});

test("category 'Direct messages' is folded", async () => {
    localStorage.setItem("discuss_sidebar_category_folded_chats", "true");
    await start();
    await openDiscuss();
    await contains(
        ".o-mail-DiscussSidebarCategory:contains('Direct messages') .oi.oi-chevron-right"
    );
    const chats_is_open = makeRecordFieldLocalId(DiscussAppCategory.localId("chats"), "is_open");
    expect(localStorage.getItem(chats_is_open)).toBe(toRawValue(false));
    expect(localStorage.getItem("discuss_sidebar_category_folded_chats")).toBe(null);
});

test("last active id of discuss app", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem(
        "mail.user_setting.discuss_last_active_id",
        `discuss.channel_${channelId}`
    );
    await start();
    await openDiscuss();
    await contains(".o-mail-Thread:contains('Welcome to #test')");
    const lastActiveId = makeRecordFieldLocalId(DiscussApp.localId(), "lastActiveId");
    expect(localStorage.getItem(lastActiveId)).toBe(toRawValue(`discuss.channel_${channelId}`));
    expect(localStorage.getItem("mail.user_setting.discuss_last_active_id")).toBe(null);
});

test("call auto focus is 'off", async () => {
    mockGetMedia();
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "test" });
    localStorage.setItem("mail_user_setting_disable_call_auto_focus", "true");
    await start();
    await openDiscuss(channelId);
    await click("[title='Start Call']");
    await click(".o-discuss-CallActionList [title='More']");
    await contains(".o-dropdown-item:contains('Autofocus speaker')");
    // correct local storage values
    const useCallAutoFocusKey = makeRecordFieldLocalId(Settings.localId(), "useCallAutoFocus");
    expect(localStorage.getItem(useCallAutoFocusKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("mail_user_setting_disable_call_auto_focus")).toBe(null);
});
