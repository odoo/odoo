import { defineLivechatModels } from "@im_livechat/../tests/livechat_test_helpers";

import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { contains, openDiscuss, start, startServer } from "@mail/../tests/mail_test_helpers";

import { beforeEach, describe, expect, test } from "@odoo/hoot";

import { Command, serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

beforeEach(() => {
    serverState.serverVersion = [99, 9]; // high version so following upgrades keep good working of feature
});

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
        livechat_operator_id: serverState.partnerId,
    });
    localStorage.setItem("discuss_sidebar_category_folded_im_livechat.category_default", "true");
    await start();
    await openDiscuss();
    await contains(".o-mail-DiscussSidebarCategory:contains('Livechat') .oi.oi-chevron-right");
    const defaultLivechat_is_open = makeRecordFieldLocalId(
        DiscussAppCategory.localId("im_livechat.category_default"),
        "is_open"
    );
    expect(localStorage.getItem(defaultLivechat_is_open)).toBe(toRawValue(false));
    expect(
        localStorage.getItem("discuss_sidebar_category_folded_im_livechat.category_default")
    ).toBe(null);
});
