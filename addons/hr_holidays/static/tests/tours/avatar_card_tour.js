import { registry } from "@web/core/registry";

const steps = [
    {
        content: "Open the chat",
        trigger: ".o-mail-DiscussSidebar-item:contains(Enguerrand Employee C2)",
        run: "click",
    },
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
        content: "Check that the employee's holiday status is displayed",
        trigger: ".o_avatar_card:contains(Back on)",
    },
    {
        content: "Check that the employee's work phone is displayed",
        trigger: ".o_avatar_card:contains(987654321)",
    },
];

registry.category("web_tour.tours").add("avatar_card_tour", {
    url: "/odoo/discuss",
    steps: () => [
        ...steps,
        {
            content: "Check that the employee's job title is displayed",
            trigger: ".o_avatar_card:contains(Test Job Title)",
        },
    ],
});

registry.category("web_tour.tours").add("avatar_card_tour_no_access", {
    url: "/odoo/discuss",
    steps: () => steps,
});
