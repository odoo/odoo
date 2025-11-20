import {
    click,
    contains,
    defineMailModels,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("Message replies panel: basic rendering", async () => {
    const pyEnv = await startServer();
    const johnPartnerId = pyEnv["res.partner"].create({ name: "John" });
    const channelId = pyEnv["discuss.channel"].create({ name: "general" });
    const defaultFields = {
        message_type: "comment",
        model: "discuss.channel",
        res_id: channelId,
    };
    const ideasMessageId = pyEnv["mail.message"].create({
        ...defaultFields,
        body: "We need campaign ideas",
    });
    pyEnv["mail.message"].create({
        ...defaultFields,
        body: "I wrote down some ideas on the whiteboard",
        author_id: johnPartnerId,
    });
    const webinarMessageId = pyEnv["mail.message"].create({
        ...defaultFields,
        body: "How about a youtube video?",
        parent_id: ideasMessageId,
    });
    pyEnv["mail.message"].create({
        ...defaultFields,
        body: "I will be off all week",
        author_id: johnPartnerId,
    });
    pyEnv["mail.message"].create({
        ...defaultFields,
        body: "We already did that last month",
        parent_id: webinarMessageId,
        author_id: johnPartnerId,
    });
    pyEnv["mail.message"].create({
        ...defaultFields,
        body: "Let's have a meeting to brainstorm some ideas",
        parent_id: ideasMessageId,
    });
    pyEnv["mail.message"]._applyComputesAndValidate();
    await start();
    await openDiscuss(channelId);
    // The replies indicator is shown and clicking it opens the replies panel
    await click(".o-mail-Message:contains('We need campaign ideas') small[title='2 Replies']");
    await contains(".o-mail-ActionPanel .o-mail-ActionPanel-header:contains('Replies')");
    // The replies panel shows all descendant messages
    await contains(".o-mail-ActionPanel .o-mail-Message", { count: 4 });
    await contains(".o-mail-ActionPanel .o-mail-Message", { text: "We need campaign ideas" });
    await contains(".o-mail-MessageReplies-descendants .o-mail-Message:nth-child(1)", {
        text: "How about a youtube video?",
    });
    await contains(".o-mail-MessageReplies-descendants .o-mail-Message:nth-child(2)", {
        text: "We already did that last month",
    });
    await contains(".o-mail-MessageReplies-descendants .o-mail-Message:nth-child(3)", {
        text: "Let's have a meeting to brainstorm some ideas",
    });
    // Clicking the replies indicator of another message changes the replies
    await click(
        ".o-mail-Thread .o-mail-Message:contains('How about a youtube video?') small[title='1 Reply']"
    );
    await contains(".o-mail-ActionPanel .o-mail-Message", { count: 2 });
    await contains(".o-mail-ActionPanel .o-mail-Message", { text: "How about a youtube video?" });
    await contains(".o-mail-MessageReplies-descendants .o-mail-Message:nth-child(1)", {
        text: "We already did that last month",
    });
    // Clicking the replies indicator again closes the replies panel
    await click(".o-mail-Message:contains('How about a youtube video?') small[title='1 Reply']");
    await contains(".o-mail-ActionPanel", { count: 0 });
});
