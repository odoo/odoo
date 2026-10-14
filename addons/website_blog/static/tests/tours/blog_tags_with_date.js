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
        content: "Click on 'Tour Tag 1'",
        trigger: ":iframe #o_wblog_sidebar a.o_post_link_js_loaded:contains('Tour Tag 1')",
        run: "click",
    },
    {
        content: "Check 'Tour Tag 1' has been added",
        trigger: ":iframe #o_wblog_posts_loop .o_filter_tag:contains('Tour Tag 1')",
    },
    {
        content: "Click on 'Tour Tag 2'",
        trigger: ":iframe #o_wblog_sidebar a.o_post_link_js_loaded:contains('Tour Tag 2')",
        run: "click",
    },
    {
        content: "Check 'Tour Tag 2' has been added",
        trigger: ":iframe #o_wblog_posts_loop .o_filter_tag:contains('Tour Tag 2')",
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
        trigger: ":iframe #o_wblog_posts_loop span>i[data-icon='calendar_today']",
    },
    {
        content: "Check both tags are present after addition of date filter",
        trigger:
            ":iframe #o_wblog_posts_loop:has(i[data-icon='calendar_today']):has(.o_filter_tag:contains('Tour Tag 1')):has(.o_filter_tag:contains('Tour Tag 2'))",
    },
    {
        content: "Remove the date filter",
        trigger: ":iframe #o_wblog_posts_loop span:has(i[data-icon='calendar_today']) a.o_post_link_js_loaded",
        run: "click",
    },
    {
        content: "Date filter should not be present",
        trigger: ":iframe #o_wblog_posts_loop span:not(:has(i[data-icon='calendar_today']))",
    },
    {
        content: "Check both tags are present after removal of date filter",
        trigger:
            ":iframe #o_wblog_posts_loop:not(:has(i[data-icon='calendar_today'])):has(.o_filter_tag:contains('Tour Tag 1')):has(.o_filter_tag:contains('Tour Tag 2'))",
    },
]);
