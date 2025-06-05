import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

registerWebsitePreviewTour(
    "blog_sidebar_with_date_and_tag",
    {
        url: "/blog",
    },
    () => [
        {
            content: "Click on the 'Nature' blog category to filter blog posts.",
            trigger: ":iframe b:contains('Nature')",
            run: "click",
        },
        {
            content: "Verify that the blog post list shows only posts from the 'Nature' category.",
            trigger: ":iframe #o_wblog_post_name:contains('Nature')",
        },
        {
            content: "Check if the archive dropdown contains exactly 1 option: February.",
            trigger: ":iframe select[name=archive]",
            run: function () {
                const optionEls = this.anchor.querySelectorAll("optgroup option");
                const length = optionEls.length;
                const monthName = optionEls[0].textContent;
                if (length !== 1 || !monthName.includes("February")) {
                    throw new Error("Expected 1 option in the select with February");
                }
            },
        },
        {
            content: "Click on the 'Space' blog category to switch filters.",
            trigger: ":iframe b:contains('Space')",
            run: "click",
        },
        {
            content: "Verify that the blog post list shows only posts from the 'Space' category.",
            trigger: ":iframe #o_wblog_post_name:contains('Space')",
        },
        {
            content: "Verify that the archive dropdown now contains only 1 option: January.",
            trigger: ":iframe select[name=archive]",
            run: function () {
                const optionEls = this.anchor.querySelectorAll("optgroup option");
                const length = optionEls.length;
                const monthName = optionEls[0].textContent;
                if (length !== 1 || !monthName.includes("January")) {
                    throw new Error("Expected 1 option in the select with January");
                }
            },
        },
    ]
);
