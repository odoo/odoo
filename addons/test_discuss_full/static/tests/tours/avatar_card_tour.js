import { registry } from "@web/core/registry";

const steps = [
    {
        content: "Open the avatar card popover",
        trigger: ".o-mail-Message-avatar",
        run: "click",
    },
    {
        content: "Check that the employee's work email is displayed",
        trigger: ".o_avatar_card:contains(test_employee@test.com)",
    },
    {
        content: "Check that the employee's department is displayed",
        trigger: ".o_avatar_card:contains(Test Department)",
    },
    {
        content: "Check that the employee's work phone is displayed",
        trigger: ".o_avatar_card:contains(123456789)",
    },
    {
        content: "Check that the employee's holiday status is displayed",
        trigger: ".o_avatar_card:contains(Back on)",
    },
];

registry.category("web_tour.tours").add("avatar_card_tour", {
    steps: () => [
        ...steps,
        {
            content: "Check that the employee's job title is displayed",
            trigger: ".o_avatar_card:contains(Test Job Title)",
        },
        {
            trigger: ".o-mail-ActivityMenu-counter:text('2')",
        },
        {
            trigger: ".o_switch_company_menu button",
            run: "click",
        },
        {
            trigger: `[role=button][title='Switch to Company 2']`,
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o-mail-ActivityMenu-counter:text('1')",
        },
    ],
});

registry.category("web_tour.tours").add("avatar_card_tour_no_hr_access", {
    steps: () => [
        ...steps,
        {
            content: "Check that the employee's job title is displayed",
            trigger: ":not(.o_avatar_card:contains(Test Job Title))",
        },
    ],
});
