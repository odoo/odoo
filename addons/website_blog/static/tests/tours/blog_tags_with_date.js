import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

/**
 * Makes sure that blog tags should not be removed on the addition of date filter
 * and on the removal of date filter.
 */
registerWebsitePreviewTour("blog_tags_with_date", {}, () => [
    {
        content: "Check that the sidebar is present",
        trigger: ":iframe #o_wblog_sidebar",
    },
    {
        content: "Click on 'adventure' tag",
        trigger: ":iframe #o_wblog_sidebar a.o_post_link_js_loaded:contains('adventure')",
        run: "click",
    },
    {
        content: "Check 'adventure' tag has been added",
        trigger: ":iframe #o_wblog_posts_loop span:contains('adventure')",
    },
    {
        content: "Click on 'discovery' tag",
        trigger: ":iframe #o_wblog_sidebar a.o_post_link_js_loaded:contains('discovery')",
        run: "click",
    },
    {
        content: "Check 'discovery' tag has been added",
        trigger: ":iframe #o_wblog_posts_loop span:contains('discovery')",
    },
    {
        content: "Check archive select is loaded with month options",
        trigger: ":iframe select[name=archive].o_post_link_js_loaded:has(optgroup option)",
    },
    {
        content: "Select first month",
        trigger: ":iframe select[name=archive]",
        async run({ selectByIndex }) {
            const index = [...this.anchor.options].findIndex((o) => o.closest("optgroup"));
            await selectByIndex(index);
        },
    },
    {
        content: "Check date filter has been added",
        trigger: ":iframe #o_wblog_posts_loop span>i.fa-calendar-o",
    },
    {
        content: "Check 'adventure' and 'discovery' tag is present after addition of date filter",
        trigger:
            ":iframe #o_wblog_posts_loop:has(span:contains('adventure'), span:contains('discovery'))",
    },
    {
        content: "Remove the date filter",
        trigger: ":iframe #o_wblog_posts_loop span:has(i.fa-calendar-o) a",
        run: "click",
    },
    {
        content: "Date filter should not be present",
        trigger: ":iframe #o_wblog_posts_loop span:not(:has(i.fa-calendar-o))",
    },
    {
        content: "Check 'adventure' and 'discovery' tag is present after removal of date filter",
        trigger:
            ":iframe #o_wblog_posts_loop:has(span:contains('adventure'), span:contains('discovery'))",
    },
]);
