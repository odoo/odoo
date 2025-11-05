import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";

const pollId = new URL(window.location.href).searchParams.get("test_poll_id");
registry.category("web_tour.tours").add("mail_poll_tour.js", {
    steps: () => [
        { trigger: ".o-mail-Composer [title='More Actions']", run: "click" },
        { trigger: "button:contains('Start a poll')", run: "click" },
        { trigger: ".modal-header:contains('Create a poll')" },
        { trigger: "input[name='poll_question']", run: "edit What is your favorite color?" },
        { trigger: "button:contains('Add another option'):enabled" },
        { trigger: ".o-mail-CreatePollOptionDialog input:eq(0)", run: "edit Red" },
        { trigger: ".o-mail-CreatePollOptionDialog input:eq(1)", run: "edit Green" },
        { trigger: "button:contains('Add another option')", run: "click" },
        { trigger: ".o-mail-CreatePollOptionDialog input:eq(2)", run: "edit Blue" },
        { trigger: "button:contains(Post)", run: "click" },
        { trigger: ".o-mail-Poll :contains('What is your favorite color?')" },
        { trigger: ".o-mail-Poll :contains('Select one option')" },
        { trigger: ".o-mail-Poll button:contains('Vote'):disabled" },
        { trigger: ".o-mail-PollOption:contains('Red') input:not(:checked)" },
        { trigger: ".o-mail-PollOption:contains('Green') input:not(:checked)" },
        { trigger: ".o-mail-PollOption:contains('Blue') input:not(:checked)", run: "click" },
        { trigger: ".o-mail-PollOption:contains('Blue') input:checked" },
        { trigger: ".o-mail-Poll button:contains('Vote'):enabled", run: "click" },
        { trigger: ".o-mail-PollOption:contains(Blue):contains(1 vote100 %)" },
        { trigger: ".o-mail-Poll button:contains('Remove Vote')", run: "click" },
        { trigger: ".o-mail-PollOption:contains('Blue') input:not(:checked)" },
        { trigger: ".o-mail-Message:has(.o-mail-Poll) [title='Reply']", run: "click" },
        {
            trigger:
                ".o-mail-Composer:contains('Replying to Ernest Employee') .o-mail-Composer-input",
            run: "edit Reply to the poll",
        },
        {
            trigger: ".o-mail-Composer:has(button[title='Send']:enabled) .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger:
                ".o-mail-MessageInReply:contains('What is your favorite color?') .oi-view-cohort",
        },
        { trigger: ".o-mail-PollOption:contains('Blue') input", run: "click" },
        { trigger: ".o-mail-Poll button:contains('Vote'):enabled", run: "click" },
        { trigger: ".o-mail-PollOption:contains(Blue):contains(1 vote100 %)" },
        { trigger: ".o-mail-Message:has(.o-mail-Poll)", run: "hover && click [title='Expand']" },
        { trigger: "button:contains('End Poll')", run: "click" },
        { trigger: ".o-mail-PollResult:contains(Blue)" },
        { trigger: ".o-mail-PollResult:contains('Winning Answer∙100%')" },
        {
            trigger: ".o-mail-Message:has(.o-mail-Poll)",
            run: "hover && click .o-mail-Message:has(.o-mail-Poll) [title='Expand']",
        },
        { trigger: "button:contains('Delete')", run: "click" },
        { trigger: ".modal .btn:contains(Delete)", run: "click" },
        {
            trigger:
                ".o-mail-Message:contains('This message has been removed'):not(:has(.o-mail-Poll))",
        },
        // End a poll that was not loaded to ensure all the information required by the end poll UI
        // is provided by the `_end_and_notify` method.
        {
            trigger: "body",
            run: () => rpc("/mail/poll/end", { poll_id: pollId }),
        },
        {
            trigger:
                '.o-mail-PollResult:contains(internal user (base.group_user)\'s poll "???" has ended.)',
        },
    ],
});
