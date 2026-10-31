import {
    click,
    contains,
    defineMailModels,
    hover,
    openDiscuss,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import { describe, mockTouch, test } from "@odoo/hoot";

import { Command } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("can add, replace, and remove emojis to a poll option", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Composer button[title='More Actions']");
    await click(".o-dropdown-item:text('Create Poll')");
    await contains(".modal-header:text('Create Poll')");
    await click(".o-mail-CreatePollOptionDialog:first [data-icon='sentiment_satisfied']");
    await click(".o-Emoji:text('😀')");
    await click(".o-mail-CreatePollOptionDialog:first span:text('😀')");
    await click(".o-dropdown-item:text('Replace Emoji')");
    await click(".o-Emoji:text('😁')");
    await click(".o-mail-CreatePollOptionDialog:first span:text('😁')");
    await click(".o-dropdown-item:text('Remove Emoji')");
    await contains(".o-mail-CreatePollOptionDialog:first [data-icon='sentiment_satisfied']");
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

test.tags("focus required");
test("autofocus question on poll opening and user-added options", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await click(".o-mail-Composer button[title='More Actions']");
    await click(".o-dropdown-item:text('Create Poll')");
    await contains(".modal-header:text('Create Poll')");
    await contains("input[name='poll_question']:focus");
    await click("button:text('Add another option')");
    await contains(".o-mail-CreatePollOptionDialog:eq(2) input:focus");
});

test("full label of a truncated poll option is shown in a tooltip", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        body: "",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const longLabel = "A very long poll option ".repeat(12).trim();
    pyEnv["mail.poll"].create({
        option_ids: [
            Command.create({ option_label: longLabel }),
            Command.create({ option_label: "Short" }),
        ],
        poll_question: "What do you think?",
        start_message_id: messageId,
    });
    await start();
    await openDiscuss(channelId);
    await hover(`.o-mail-PollOption span:text('${longLabel}')`);
    await contains(`.o-tooltip:text('${longLabel}')`);
    await hover(".o-mail-PollOption span:text('Short')");
    await contains(".o-mail-PollOption span[data-tooltip='']:text('Short')");
    await click(".o-mail-Poll a:text('View results')");
    await contains(".o-mail-PollOption div > span.text-truncate", { count: 2 });
    await contains(".o-tooltip", { count: 0 });
    await hover(`.o-mail-PollOption span:text('${longLabel}')`);
    await contains(`.o-tooltip:text('${longLabel}')`);
});

test("tap on the info button of a truncated poll option shows its full label", async () => {
    mockTouch(true);
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const messageId = pyEnv["mail.message"].create({
        body: "",
        model: "discuss.channel",
        res_id: channelId,
        message_type: "comment",
    });
    const longLabel = "A very long poll option ".repeat(12).trim();
    pyEnv["mail.poll"].create({
        option_ids: [
            Command.create({ option_label: longLabel }),
            Command.create({ option_label: "Short" }),
        ],
        poll_question: "What do you think?",
        start_message_id: messageId,
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-PollOption i.fa-info-circle:count(1)");
    await triggerEvents(`.o-mail-PollOption i[data-tooltip='${longLabel}']`, [
        "touchstart",
        "touchend",
        "click",
    ]);
    await contains(`.o-tooltip:text('${longLabel}')`);
    await contains(".o-mail-PollOption input:not(:checked)", { count: 2 });
    await click(`.o-mail-PollOption span:text('${longLabel}')`);
    await contains(".o-mail-PollOption input:checked");
});
