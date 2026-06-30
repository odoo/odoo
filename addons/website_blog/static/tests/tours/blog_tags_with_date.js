import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

/**
 * Makes sure that blog tags should not be removed on the addition of date filter
 * and on the removal of date filter.
 */
registerWebsitePreviewTour("blog_tags_with_date", {
    url: "/blog",
}, () => [{
        content: "Check that the sidebar is present",
        trigger: ":iframe #o_wblog_sidebar",
    }, {
        content: "Click on 'adventure' tag",
        trigger: ":iframe #o_wblog_sidebar a:contains('adventure')",
        run: "click",
    }, {
        content: "Check 'adventure' tag has been added",
        trigger: ":iframe #o_wblog_posts_loop span:contains('adventure')",
    }, {
        content: "Click on 'discovery' tag",
        trigger: ":iframe #o_wblog_sidebar a:contains('discovery')",
        run: "click",
    }, {
        content: "Check 'discovery' tag has been added",
        trigger: ":iframe #o_wblog_posts_loop span:contains('discovery')",
    }, {
        content: "Select first month",
        trigger: ":iframe select[name=archive]",
        run: function (helpers) {
            const options = Array.from(this.anchor?.options ?? []);
            const firstMonthIndex = options.findIndex((option) => option.closest("optgroup"));
            if (firstMonthIndex === -1) {
                throw new Error("Expected an option inside an optgroup in the archive select.");
            }
            return helpers.selectByIndex(firstMonthIndex, this.anchor);
        },
    }, {
        content: "Check date filter has been added",
        trigger: ":iframe #o_wblog_posts_loop span>i.fa-calendar-o",
    }, {
        content: "Check 'adventure' and 'discovery' tag is present after addition of date filter",
        trigger: ":iframe #o_wblog_posts_loop:has(span:contains('adventure'), span:contains('discovery'))",
    }, {
        content: "Remove the date filter",
        trigger: ":iframe #o_wblog_posts_loop span:has(i.fa-calendar-o) a",
        run: "click",
    }, {
        content: "Date filter should not be present",
        trigger: ":iframe #o_wblog_posts_loop span:not(:has(i.fa-calendar-o))",
    }, {
        content: "Check 'adventure' and 'discovery' tag is present after removal of date filter",
        trigger: ":iframe #o_wblog_posts_loop:has(span:contains('adventure'), span:contains('discovery'))",
    }]
);
