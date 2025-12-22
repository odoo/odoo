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
        {
            content: "Click on the 'Second Blog Post' to view its details.",
            trigger: ":iframe article a:contains('Second Blog Post')",
            run: "click",
        },
        {
            content: "Click on 'Add some' to navigate to the backend view of the blog post.",
            trigger: ":iframe #edit-in-backend",
            run: "click",
        },
        {
            content: "Verify that we are redirected to the backend blog post form view.",
            trigger: ".o_form_view",
            run: () => {
                if (!window.location.href.includes("/odoo/website/blog.post/")) {
                    throw new Error("We should be on the blog page backend view");
                }
            },
        },
    ]
);
