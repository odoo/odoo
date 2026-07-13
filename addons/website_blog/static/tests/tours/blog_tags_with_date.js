/** @odoo-module **/

import wTourUtils from "@website/js/tours/tour_utils";

/**
 * Makes sure that blog tags should not be removed on the addition of date filter
 * and on the removal of date filter.
 */
wTourUtils.registerWebsitePreviewTour("blog_tags_with_date", {
    test: true,
    url: "/blog",
}, () => [{
        content: "Check that the sidebar is present",
        trigger: "iframe #o_wblog_sidebar",
        isCheck: true,
    }, {
        content: "Click on 'adventure' tag",
        trigger: "iframe #o_wblog_sidebar a:contains('adventure')",
    }, {
        content: "Check 'adventure' tag has been added",
        trigger: "iframe #o_wblog_posts_loop span:contains('adventure')",
        isCheck: true,
    }, {
        content: "Click on 'discovery' tag",
        trigger: "iframe #o_wblog_sidebar a:contains('discovery')",
    }, {
        content: "Check 'discovery' tag has been added",
        trigger: "iframe #o_wblog_posts_loop span:contains('discovery')",
        isCheck: true,
    }, {
        content: "Select first month",
        trigger: "iframe select[name=archive]",
        run: "text option 2",
    }, {
        content: "Check date filter has been added",
        trigger: "iframe #o_wblog_posts_loop span>i.fa-calendar-o",
        isCheck: true,
    }, {
        content: "Check 'adventure' and 'discovery' tag is present after addition of date filter",
        trigger: "iframe #o_wblog_posts_loop:has(span:contains('adventure'), span:contains('discovery'))",
        isCheck: true,
    }, {
        content: "Remove the date filter",
        trigger: "iframe #o_wblog_posts_loop span:has(i.fa-calendar-o) a",
    }, {
        content: "Date filter should not be present",
        trigger: "iframe #o_wblog_posts_loop span:not(:has(i.fa-calendar-o))",
        isCheck: true,
    }, {
        content: "Check 'adventure' and 'discovery' tag is present after removal of date filter",
        trigger: "iframe #o_wblog_posts_loop:has(span:contains('adventure'), span:contains('discovery'))",
        isCheck: true,
    }]
);
