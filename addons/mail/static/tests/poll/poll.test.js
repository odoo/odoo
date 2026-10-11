import {
    click,
    defineMailModels,
    hover,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";

describe.current.tags("desktop");
defineMailModels();

test("can add, replace, and remove emojis to a poll option", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html:focus:count(1)");
    await click(".o-mail-Composer button[title='More Actions']");
    await click(".o-dropdown-item:text('Create Poll')");
    await waitFor(".modal-header:text('Create Poll'):count(1)");
    await click(".o-mail-CreatePollOptionDialog:first [data-icon='sentiment_satisfied']");
    await click(".o-Emoji:text('😀')");
    await click(".o-mail-CreatePollOptionDialog:first span:text('😀')");
    await click(".o-dropdown-item:text('Replace Emoji')");
    await click(".o-Emoji:text('😁')");
    await click(".o-mail-CreatePollOptionDialog:first span:text('😁')");
    await click(".o-dropdown-item:text('Remove Emoji')");
    await waitFor(
        ".o-mail-CreatePollOptionDialog:first [data-icon='sentiment_satisfied']:count(1)"
    );
});

test("poll creation should be disabled during message editing", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    pyEnv["mail.message"].create({
        body: "Hello world",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html:focus:count(1)");
    await click(".o-mail-Composer button[title='More Actions']");
    await waitFor(".o-dropdown-item:text('Create Poll'):count(1)");
    await hover(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:text('Edit')");
    await waitFor(".o-mail-Message .o-mail-Composer-html:focus:count(1)");
    await click(".o-mail-Message .o-mail-Composer button[title='More Actions']");
    await waitFor(".o-dropdown-item:text('Attach Files'):count(1)");
    await waitForNone(".o-dropdown-item:text('Create Poll')");
});

test.tags("focus required");
test("autofocus question on poll opening and user-added options", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html:focus:count(1)");
    await click(".o-mail-Composer button[title='More Actions']");
    await click(".o-dropdown-item:text('Create Poll')");
    await waitFor(".modal-header:text('Create Poll'):count(1)");
    await waitFor("input[name='poll_question']:focus:count(1)");
    await click("button:text('Add another option')");
    await waitFor(".o-mail-CreatePollOptionDialog:eq(2) input:focus:count(1)");
});
