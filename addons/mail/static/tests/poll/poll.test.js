import {
    click,
    defineMailModels,
    hover,
    openDiscuss,
    start,
    startServer,
    triggerEvents,
} from "@mail/../tests/mail_test_helpers";
import {
    advanceTime,
    describe,
    expect,
    mockDate,
    mockTouch,
    test,
    waitFor,
    waitForNone,
} from "@odoo/hoot";

import { editTime, getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
import { Command, contains, onRpc } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineMailModels();

test("can add, replace, and remove emojis to a poll option", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    await start();
    await openDiscuss(channelId);
    await waitFor(".o-mail-Composer-html:focus:count(1)");
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
    await contains(".o-mail-Composer button[title='More Actions']:count(1)").click();
    await contains(".o-dropdown-item:text('Create Poll'):count(1)").click();
    await waitFor(".modal-header:text('Create Poll'):count(1)");
    await waitFor("input[name='poll_question']:focus:count(1)");
    await contains("button:text('Add another option'):count(1)").click();
    await waitFor(".o-mail-CreatePollOptionDialog:eq(2) input:focus:count(1)");
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
    await waitFor(`.o-tooltip:text('${longLabel}'):count(1)`);
    await hover(".o-mail-PollOption span:text('Short')");
    await advanceTime(1000);
    await waitForNone(".o-tooltip");
    await contains(".o-mail-Poll a:text('View results'):count(1)").click();
    await waitFor(".o-mail-PollOption div > span.text-truncate:count(2)");
    await waitForNone(".o-tooltip");
    await hover(`.o-mail-PollOption span:text('${longLabel}')`);
    await waitFor(`.o-tooltip:text('${longLabel}'):count(1)`);
    await contains(".o-mail-Poll a:text('0 votes'):count(1)").click();
    await hover(`.o-mail-PollVotesPanel span:text('${longLabel}')`);
    await waitFor(`.o-tooltip:text('${longLabel}'):count(1)`);
});

test("full label of a truncated winning option is shown in a tooltip", async () => {
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    const [startMessageId, endMessageId] = pyEnv["mail.message"].create(
        [1, 2].map(() => ({
            body: "",
            model: "discuss.channel",
            res_id: channelId,
            message_type: "comment",
        }))
    );
    const longLabel = "A very long poll option ".repeat(12).trim();
    const optionId = pyEnv["mail.poll.option"].create({ option_label: longLabel });
    pyEnv["mail.poll"].create({
        end_message_id: endMessageId,
        option_ids: [optionId],
        poll_question: "What do you think?",
        start_message_id: startMessageId,
        winning_option_id: optionId,
    });
    await start();
    await openDiscuss(channelId);
    await hover(`.o-mail-PollResult p:text('${longLabel}')`);
    await waitFor(`.o-tooltip:text('${longLabel}'):count(1)`);
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
    await waitFor(".o-mail-PollOption i.oi[data-icon='info']:count(1)");
    await triggerEvents(`.o-mail-PollOption i[data-tooltip='${longLabel}']`, [
        "touchstart",
        "touchend",
        "click",
    ]);
    await waitFor(`.o-tooltip:text('${longLabel}'):count(1)`);
    await waitFor(".o-mail-PollOption input:not(:checked):count(2)");
    await contains(`.o-mail-PollOption span:text('${longLabel}'):count(1)`).click();
    await waitFor(".o-mail-PollOption input:checked:count(1)");
});

test("can pick a custom end time for a poll", async () => {
    mockDate("2026-11-27 10:02:00");
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc("/mail/poll/create", async (request) => {
        const { params } = await request.json();
        expect(params.duration).toBe(undefined);
        expect(params.end_dt.startsWith("2026-11-30 ")).toBe(true);
        expect.step("poll_create");
    });
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer button[title='More Actions']").click();
    await contains(".o-dropdown-item:text('Create Poll')").click();
    await contains("input[name='poll_question']").edit("Lunch?");
    await contains(".o-mail-CreatePollOptionDialog:eq(0) input").edit("Pizza");
    await contains(".o-mail-CreatePollOptionDialog:eq(1) input").edit("Burger");
    await contains("button[name='poll_duration']:text('10 minutes')").click();
    await contains(".o-dropdown-item:text('Custom')").click();
    // No end time is preselected.
    await waitFor(".o_datetime_picker");
    await waitFor("button[name='poll_duration']:text('Custom')");
    // Clicking the toggler while the picker is open only closes the picker.
    await contains("button[name='poll_duration']").click();
    await waitForNone(".o_datetime_picker");
    await waitForNone(".o-dropdown-item:text('Custom')");
    await contains(".modal-footer button:text('Post')").click();
    await waitFor(".text-danger:text('Please select an end time.')");
    expect.verifySteps([]);
    // Selecting "Custom" again reopens the picker; the label follows the picked value.
    await contains("button[name='poll_duration']").click();
    await contains(".o-dropdown-item:text('Custom')").click();
    await waitForNone(".text-danger:text('Please select an end time.')");
    await contains(getPickerCell("30")).click();
    await waitFor("button[name='poll_duration']:text('11/30/2026 11:00')");
    await editTime("14:30");
    await waitFor("button[name='poll_duration']:text('11/30/2026 14:30')");
    await contains(".o_datetime_picker button:text('Apply')").click();
    await waitForNone(".o_datetime_picker");
    await waitFor("button[name='poll_duration']:text('11/30/2026 14:30')");
    // Clearing the end time brings back "Custom".
    await contains("button[name='poll_duration']").click();
    await contains(".o-dropdown-item:text('Custom')").click();
    await contains(".o_datetime_picker button[title='Clear']").click();
    await waitForNone(".o_datetime_picker");
    await waitFor("button[name='poll_duration']:text('Custom')");
    await waitForNone(".text-danger");
    await contains("button[name='poll_duration']").click();
    await contains(".o-dropdown-item:text('Custom')").click();
    await contains(getPickerCell("30")).click();
    await editTime("14:30");
    await contains(".o_datetime_picker button:text('Apply')").click();
    await waitFor("button[name='poll_duration']:text('11/30/2026 14:30')");
    await contains(".modal-footer button:text('Post')").click();
    await expect.waitForSteps(["poll_create"]);
});

test("custom poll end time in the past shows an error and cannot be posted", async () => {
    mockDate("2026-11-27 10:02:00"); // 11:02 in the test timezone (UTC+1)
    const pyEnv = await startServer();
    const channelId = pyEnv["discuss.channel"].create({ name: "General" });
    onRpc("/mail/poll/create", () => expect.step("poll_create"));
    await start();
    await openDiscuss(channelId);
    await contains(".o-mail-Composer button[title='More Actions']").click();
    await contains(".o-dropdown-item:text('Create Poll')").click();
    await contains("input[name='poll_question']").edit("Lunch?");
    await contains(".o-mail-CreatePollOptionDialog:eq(0) input").edit("Pizza");
    await contains(".o-mail-CreatePollOptionDialog:eq(1) input").edit("Burger");
    await contains("button[name='poll_duration']").click();
    await contains(".o-dropdown-item:text('Custom')").click();
    // A past time of today is accepted by the picker, then reported as an error.
    await contains(getPickerCell("27")).click();
    await editTime("10:30");
    await contains(".o_datetime_picker button:text('Apply')").click();
    await waitForNone(".o_datetime_picker");
    await waitFor("button[name='poll_duration']:text('11/27/2026 10:30')");
    await waitFor(".text-danger:text('Choose an end time in the future.')");
    await contains(".modal-footer button:text('Post')").click();
    expect.verifySteps([]);
    // Switching back to a preset clears the error and allows posting.
    await contains("button[name='poll_duration']").click();
    await contains(".o-dropdown-item:text('1 hour')").click();
    await waitForNone(".text-danger:text('Choose an end time in the future.')");
    await contains(".modal-footer button:text('Post')").click();
    await expect.waitForSteps(["poll_create"]);
});
