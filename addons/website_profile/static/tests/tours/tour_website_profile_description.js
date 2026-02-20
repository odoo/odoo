import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('website_profile_description', {
    url: "/profile/users",
    steps: () => [{
        content: "Click on one user profile card",
        trigger: "div[onclick]:contains(\"test_user\")",
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Edit profile",
        trigger: "a:contains('EDIT PROFILE')",
        run: "click",
    }, {
        content: "Add some content",
        trigger: ".odoo-editor-editable",
        run: "editor content <p>code here</p>",
    }, {
        content: "Save changes",
        trigger: "button:contains('Update')",
        run: "click",
        expectUnloadPage: true,
    }, {
        content: "Check the content is saved",
        trigger: "span[data-oe-field='website_description']:contains('content <p>code here</p>')",
    }]
})

registry.category("web_tour.tours").add("website_profile_portal_access", {
    url: "/profile/users",
    steps: () => [
        {
            content: "Ensure portal can see 2 badges for Bob",
            trigger: 'tr:contains("Bob"):contains("2 Badges")',
        },
        {
            content: "Ensure portal can see 1 badge for Alice",
            trigger: 'tr:contains("Alice"):contains("1 Badges")',
        },
        {
            content: `Ensure portal can't see John as he is not published.
                      There must be only 2 rows in the table`,
            trigger: 'table:contains("Bob") tr:nth-of-type(2):last-child',
        },
        {
            content: "Click on one user profile card",
            trigger: 'tr:contains("Bob")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Ensure portal can see 2 badges for Bob",
            trigger: 'tr:contains("Badges") td:contains("2")',
        },
        {
            content: "Ensure portal can see the name of badges",
            trigger: 'div:has(div:contains("Good Job")):has(div:contains("Problem Solver"))',
        },
        {
            content: "Ensure the image of the badge is displayed",
            trigger: 'img[src^="/web/image/gamification.badge/"][alt="Good Job"]',
            run: async function () {
                if (
                    (await fetch(this.anchor.src)).headers.get("Content-Disposition") !==
                    'inline; filename="Good Job.png"'
                ) {
                    throw new Error("The image of the badge is not displayed as expected");
                }
            },
        },
        {
            content: "Ensure the image of the rank is displayed",
            trigger: 'img[src^="/web/image/gamification.karma.rank/"][alt="Bachelor"]',
            run: async function () {
                if (
                    (await fetch(this.anchor.src)).headers.get("Content-Disposition") !==
                    "inline; filename=Bachelor.svg"
                ) {
                    throw new Error("The image of the rank is not displayed as expected");
                }
            },
        },
    ],
});
