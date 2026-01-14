import { describe, expect, test } from "@odoo/hoot";
import { patchBrowserNotification, start, startServer } from "@mail/../tests/mail_test_helpers";
import { makeRecordFieldLocalId } from "@mail/model/misc";
import { toRawValue } from "@mail/utils/common/local_storage";
import { getService, serverState } from "@web/../tests/web_test_helpers";
import { DiscussAppCategory } from "@mail/discuss/core/public_web/discuss_app/discuss_app_category_model";
import { defineLivechatModels } from "./livechat_test_helpers";

describe.current.tags("desktop");
defineLivechatModels();

test("Preserves force hide of of livechat looking for help", async () => {
    // From dev tools can force hide a category like "looking for help", by setting `DiscussAppCategory.hidden = true`
    localStorage.setItem("mail.sidebar_category_im_livechat.category_need_help_hidden", "true");
    patchBrowserNotification("default");
    const LOOKING_FOR_HELP_CATEGORY_HIDDEN_LS = makeRecordFieldLocalId(
        DiscussAppCategory.localId("im_livechat.category_need_help"),
        "hidden"
    );
    const pyEnv = await startServer();
    pyEnv["res.users"].write([serverState.userId], {
        group_ids: pyEnv["res.groups"]
            .search_read([["id", "=", serverState.groupLivechatId]])
            .map(({ id }) => id),
    });
    await start();
    expect(
        getService("mail.store").DiscussAppCategory.get("im_livechat.category_need_help").hidden
    ).toBe(true);
    expect(localStorage.getItem(LOOKING_FOR_HELP_CATEGORY_HIDDEN_LS)).toBe(toRawValue(true));
    expect(
        localStorage.getItem("mail.sidebar_category_im_livechat.category_need_help_hidden")
    ).toBe(null);
});
