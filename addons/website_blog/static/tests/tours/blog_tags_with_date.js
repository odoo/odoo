/** @odoo-module **/

import { clickOnSave, registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

/**
 * Makes sure that blog tags should not be removed on the addition of date filter
 * and on the removal of date filter.
 */
registerWebsitePreviewTour("blog_tags_with_date", {
    url: "/blog",
    edition: true,
}, () => [{
        content: "Click on first blog",
        trigger: ":iframe article[name=blog_post] a",
        run: "click",
    }, {
        content: "Click on sidebar option",
        trigger: "we-customizeblock-options we-button[data-customize-website-views='website_blog.opt_blog_sidebar_show'] we-checkbox",
        run: "click"
    },
    ...clickOnSave(),
    {
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
        run: "selectByLabel October",
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
