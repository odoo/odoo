import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_poll_tour.js", {
    steps: () => [
        { trigger: ".o-mail-Composer [title='More Actions']", run: "click" },
        { trigger: "button:contains('Start a poll')", run: "click" },
        { trigger: ".modal-header:contains('Create a poll')" },
        { trigger: "input[name='poll_question']", run: "edit What is your favorite color?" },
        { trigger: "button:contains('Add another option'):disabled" },
        { trigger: ".o-mail-CreatePollOptionDialog input:eq(0)", run: "edit Red" },
        { trigger: ".o-mail-CreatePollOptionDialog input:eq(1)", run: "edit Green" },
        { trigger: "button:contains('Add another option'):enabled", run: "click" },
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
        { trigger: ".o-mail-Composer button[title='More Actions']", run: "click" },
        { trigger: ".o-mail-Message:has(.o-mail-Poll) [title='Reply']", run: "click" },
        {
            trigger:
                ".o-mail-Composer:contains('Replying to internal (base.group_user)') .o-mail-Composer-input",
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
        { trigger: ".o-mail-PollResult:contains('Winning Option∙100%')" },
        { trigger: ".o-mail-Message:has(.o-mail-Poll)", run: "hover && click [title='Expand']" },
        { trigger: "button:contains('Delete')", run: "click" },
        { trigger: ".modal .btn:contains(Delete)", run: "click" },
        {
            trigger:
                ".o-mail-Message:contains('This message has been removed'):not(:has(.o-mail-Poll))",
        },
    ],
});
