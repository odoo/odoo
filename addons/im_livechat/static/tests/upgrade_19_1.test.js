import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { DiscussApp } from "@mail/core/public_web/discuss_app/discuss_app_model";
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { click, contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";

import { describe, expect, test } from "@odoo/hoot";

import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("category 'Livechat' is folded", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                livechat_member_type: "agent",
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    localStorage.setItem("discuss_sidebar_category_folded_im_livechat.category_default", "true");
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Live Chat') .oi.oi-chevron-right");
    const defaultLivechat_is_open = makeRecordFieldLocalId(
        DiscussAppCategory.localId("im_livechat.category_default"),
        "is_open"
    );
    expect(localStorage.getItem(defaultLivechat_is_open)).toBe(toRawValue(false));
    expect(
        localStorage.getItem("discuss_sidebar_category_folded_im_livechat.category_default")
    ).toBe(null);
});

test("livechat info default open is 'off'", async () => {
    const pyEnv = await startServer();
    const guestId = pyEnv["mail.guest"].create({ name: "Visitor" });
    const channelId = pyEnv["discuss.channel"].create({
        channel_member_ids: [
            Command.create({
                livechat_member_type: "agent",
                partner_id: serverState.partnerId,
            }),
            Command.create({ guest_id: guestId, livechat_member_type: "visitor" }),
        ],
        channel_type: "livechat",
    });
    localStorage.setItem("im_livechat.no_livechat_info_default_open", "true");
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-DiscussContent-threadName[title='Visitor']");
    await contains("button[name='livechat-info']");
    await contains(".o-livechat-ChannelInfoList", { count: 0 });
    const isLivechatInfoPanelOpenByDefaultKey = makeRecordFieldLocalId(
        DiscussApp.localId(),
        "isLivechatInfoPanelOpenByDefault"
    );
    expect(localStorage.getItem(isLivechatInfoPanelOpenByDefaultKey)).toBe(toRawValue(false));
    expect(localStorage.getItem("im_livechat.no_livechat_info_default_open")).toBe(null);
    await click("button[name='livechat-info']");
    await contains(".o-livechat-ChannelInfoList");
    expect(localStorage.getItem(isLivechatInfoPanelOpenByDefaultKey)).toBe(null);
    await click("button[name='livechat-info']");
    await contains(".o-livechat-ChannelInfoList", { count: 0 });
    expect(localStorage.getItem(isLivechatInfoPanelOpenByDefaultKey)).toBe(toRawValue(false));
});
