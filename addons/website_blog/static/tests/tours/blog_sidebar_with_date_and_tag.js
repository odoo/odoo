import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";

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
            content: "Check if the archive dropdown contains exactly 1 options January.",
            trigger: ":iframe select[name=archive]",
            run: function () {
                const length = this.anchor.querySelectorAll("optgroup option").length;
                if (length !== 1) {
                    throw new Error("There should be 1 options in the select");
                }
            },
        },
        {
            content: "Click on the 'Space' blog category to switch filters.",
            trigger: ":iframe b:contains('Space')",
            run: "click",
        },
        {
            content: "Verify that the archive dropdown now contains only 1 option (February).",
            trigger: ":iframe select[name=archive]",
            run: function () {
                const length = this.anchor.querySelectorAll("optgroup option").length;
                if (length !== 1) {
                    throw new Error("There should be 1 options in the select");
                }
            },
        },
        {
            content: "Click on a blog post to view its details.",
            trigger: ":iframe article a",
            run: "click",
        },
        ...clickOnEditAndWaitEditMode(),
        {
            content: "Click on the blog post sidebar to edit settings.",
            trigger: ":iframe #o_wblog_post_sidebar",
            run: "click",
        },
        {
            content: "Toggle the blog post layout options.",
            trigger: "we-toggler:contains('Title Inside Cover')",
            run: "click",
        },
        {
            content: "Change the blog post layout to 'Title Above Cover'.",
            trigger: "we-button:contains('Title Above Cover')",
            run: "click",
        },
        {
            content: "Ensure that the comment icon is not visible in the blog post as there are no comments.",
            trigger: ":iframe #title div.text-muted",
            run: function () {
                const isCommentShow = this.anchor.querySelector(".fa-comment");
                if (isCommentShow) {
                    throw new Error("The comment icon should be visible");
                }
            },
        },
        ...clickOnSave(),
        {
            content: "Click on 'Edit in Backend' to navigate to the backend view of the blog post.",
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
