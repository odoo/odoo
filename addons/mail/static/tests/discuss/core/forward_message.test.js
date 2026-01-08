import {
    click,
    contains,
    defineMailModels,
    insertText,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";

import { describe, test } from "@odoo/hoot";

import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("Should redirect the user to the target channel once a message is forwarded", async () => {
    const pyEnv = await startServer();
    const [sourceChannelId] = pyEnv["discuss.channel"].create([
        { name: "Source Channel" },
        { name: "Target Channel" },
    ]);
    pyEnv["mail.message"].create({
        author_id: serverState.partnerId,
        body: "hola amigo, a message to forward!",
        model: "discuss.channel",
        res_id: sourceChannelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(sourceChannelId);
    await contains(".o-mail-Message-content", { text: "hola amigo, a message to forward!" });
    await click(".o-mail-Message-actions [title='Expand']");
    await click(".dropdown-item", { text: "Forward" });
    await contains(".modal-dialog", { text: "Forward To" });
    await contains(".o-mail-Forward-core", { text: "hola amigo, a message to forward!" });
    await insertText(".o-discuss-SelectableList-search", "Target Channel");
    await contains(".list-group-item", { text: "Target Channel" });
    await click(".list-group-item", { text: "Target Channel" });
    await contains(".list-group-item input[type='checkbox']:checked");
    await insertText("textarea[placeholder='Add an optional message...']", "Check this out!");
    await click("button", { text: "Send" });
    await contains(".modal-dialog", { count: 0 });
    await contains(".o-mail-DiscussContent-threadName[title='Target Channel']");
    await contains(".o-mail-Message-bubble", { text: "hola amigo, a message to forward!" });
    await contains(".o-mail-Message-bubble", { text: "Forwarded" });
    await contains(".o-mail-Message-content", { text: "Check this out!" });
    await click(".o-mail-ForwardedMessage-link");
    await contains(".o-mail-DiscussContent-threadName[title='Source Channel']");
    await contains(".o-mail-Message.o-highlighted", { text: "hola amigo, a message to forward!" });
});
