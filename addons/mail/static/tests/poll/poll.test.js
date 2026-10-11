import {
    click,
    defineMailModels,
    hover,
    openDiscuss,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { describe, test, waitFor, waitForNone } from "@odoo/hoot";
import { contains } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("can add, replace, and remove emojis to a poll option", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer button[title='More Actions']:count(1)").click();
    await contains(".o-dropdown-item:text('Create Poll'):count(1)").click();
    await waitFor(".modal-header:text('Create Poll'):count(1)");
    await contains(
        ".o-mail-CreatePollOptionDialog:first [data-icon='sentiment_satisfied']:count(1)"
    ).click();
    await contains(".o-Emoji:text('😀'):count(1)").click();
    await contains(".o-mail-CreatePollOptionDialog:first span:text('😀'):count(1)").click();
    await contains(".o-dropdown-item:text('Replace Emoji'):count(1)").click();
    await contains(".o-Emoji:text('😁'):count(1)").click();
    await contains(".o-mail-CreatePollOptionDialog:first span:text('😁'):count(1)").click();
    await contains(".o-dropdown-item:text('Remove Emoji'):count(1)").click();
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
    await click(".o-mail-Composer button[title='More Actions']");
    await waitFor(".o-dropdown-item:text('Create Poll'):count(1)");
    await hover(".o-mail-Message");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:text('Edit')");
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
    await contains(".o-mail-Composer button[title='More Actions']:count(1)").click();
    await contains(".o-dropdown-item:text('Create Poll'):count(1)").click();
    await waitFor(".modal-header:text('Create Poll'):count(1)");
    await waitFor("input[name='poll_question']:focus:count(1)");
    await contains("button:text('Add another option'):count(1)").click();
    await waitFor(".o-mail-CreatePollOptionDialog:eq(2) input:focus:count(1)");
});
