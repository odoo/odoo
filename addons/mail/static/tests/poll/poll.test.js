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

test("can add, replace, and remove emojis to a poll option", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Composer button[title='More Actions']");
    await click(".o-dropdown-item:text('Create Poll')");
    await contains(".modal-header:text('Create a poll')");
    await click(".o-mail-CreatePollOptionDialog:first .fa-smile-o");
    await click(".o-Emoji:text('😀')");
    await click(".o-mail-CreatePollOptionDialog:first span:text('😀')");
    await click(".o-dropdown-item:text('Replace Emoji')");
    await click(".o-Emoji:text('😁')");
    await click(".o-mail-CreatePollOptionDialog:first span:text('😁')");
    await click(".o-dropdown-item:text('Remove Emoji')");
    await contains(".o-mail-CreatePollOptionDialog:first .fa-smile-o");
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
    await contains(".o-dropdown-item:text('Create Poll')");
    await click(".o-mail-Message [title='Expand']");
    await click(".o-dropdown-item:text('Edit')");
    await click(".o-mail-Message .o-mail-Composer button[title='More Actions']");
    await contains(".o-dropdown-item:text('Attach Files')");
    await contains(".o-dropdown-item:text('Create Poll')", { count: 0 });
});
