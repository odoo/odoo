/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

wTourUtils.registerWebsitePreviewTour(
    "blog_sidebar_with_date_and_tag",
    {
        test: true,
        url: "/blog",
    },
    () => [
        {
            content: "Click on the 'Nature' blog category to filter blog posts.",
            trigger: "iframe b:contains('Nature')",
        },
        {
            content: "Check if the archive dropdown contains exactly 1 option: February.",
            trigger: "iframe select[name=archive]",
            run: function () {
                const optionEls = this.$anchor[0].querySelectorAll("optgroup option");
                const length = optionEls.length;
                const monthName = optionEls[0].textContent;
                if (length !== 1 || !monthName.includes("February")) {
                    throw new Error("Expected 1 option in the select with February");
                }
            },
        },
        {
            content: "Click on the 'Space' blog category to switch filters.",
            trigger: "iframe b:contains('Space')",
        },
        {
            content: "Verify that the archive dropdown now contains only 1 option: January.",
            trigger: "iframe select[name=archive]",
            run: function () {
                const optionEls = this.$anchor[0].querySelectorAll("optgroup option");
                const length = optionEls.length;
                const monthName = optionEls[0].textContent;
                if (length !== 1 || !monthName.includes("January")) {
                    throw new Error("Expected 1 option in the select with January");
                }
            },
        },
    ]
);
