import { describe, test } from "@odoo/hoot";
import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("keep separator when message is deleted", async () => {
    const pyEnv = await startServer();
    const generalId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create([
        {
            body: "message 0",
            message_type: "comment",
            model: "discuss.channel",
            author_id: serverState.partnerId,
            res_id: generalId,
        },
        {
            body: "message 1",
            message_type: "comment",
            model: "discuss.channel",
            author_id: serverState.partnerId,
            res_id: generalId,
        },
    ]);
    await start();
    await openDiscuss(generalId);
    await contains(".o-mail-Message", { count: 2 });
    $(".o-mail-Composer-input").blur();
    await click("[title='Expand']", {
        parent: [".o-mail-Message", { text: "message 0" }],
    });
    await click(".o-mail-Message-moreMenu [title='Mark as Unread']");
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 0" });
    await click("[title='Expand']", {
        parent: [".o-mail-Message", { text: "message 0" }],
    });
    await click(".o-mail-Message-moreMenu [title='Delete']");
    await click("button", { text: "Confirm" });
    await contains(".o-mail-Message", { text: "message 0", count: 0 });
    await contains(".o-mail-Thread-newMessage ~ .o-mail-Message", { text: "message 1" });
});
