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
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineWebsiteLivechatModels();

test("Can create a new record as livechat operator with a custom livechat username", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({ name: "Harry" });
    pyEnv["res.partner"].write([serverState.partnerId], {
        user_livechat_username: "MitchellOp",
    });
    const channelId = pyEnv["discuss.channel"].create({
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
