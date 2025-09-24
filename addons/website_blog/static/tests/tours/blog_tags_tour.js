import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from "@website/js/tours/tour_utils";
import { stepUtils } from "@web_tour/tour_utils";

/**
 * Makes sure that blog tags can be created and removed.
 */
registerWebsitePreviewTour(
    "blog_tags",
    {
        url: "/blog",
    },
    () => [
        stepUtils.waitIframeIsReady(),
        {
            content: "Go to the 'Post Test' blog",
            trigger: ":iframe article[name=blog_post] a:contains('Post Test')",
            run: "click",
        },
        {
            content: "Ensure that the blog is opened",
            trigger: ":iframe h1.o_wblog_post_name",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet("#o_wblog_post_top .o_wblog_post_page_cover"),
        {
            content: "Open tag dropdown",
            trigger: "[data-label='Tags'] button.o_select_menu_toggler",
            run: "click",
        },
        ...stepUtils.editSelectMenuInput(".o_select_menu_input", "testtag"),
        {
            content: "Save tag",
            trigger: ".dropdown-menu a.o_we_m2o_create",
            run: "click",
        },
        {
            content: "Verify tag appears in options",
            trigger: "[data-label='Tags'] table input[data-name='testtag']",
        },
        ...clickOnSave(),
        {
            content: "Verify tag appears in blog post",
            trigger: ":iframe #o_wblog_post_content .badge:contains('testtag')",
        },
        ...clickOnEditAndWaitEditMode(),
        ...clickOnSnippet("#o_wblog_post_top .o_wblog_post_page_cover"),
        {
            content: "Remove tag",
            trigger: "[data-label='Tags'] table tr:has(input[data-name='testtag']) button.fa-minus",
            run: "click",
        },
        {
            content: "Verify tag does not appear in options anymore",
            trigger: "[data-label='Tags'] table:not(:has(input[data-name='testtag']))",
        },
        ...clickOnSave(),
        {
            content: "Verify tag does not appear in blog post anymore",
            trigger: ":iframe #o_wblog_post_content div:has(.badge):not(:contains('testtag'))",
        },
        {
            trigger: ":iframe .o_wblog_post_title:contains(post test)",
        },
        {
            content: "Go back to /blog",
            trigger: ":iframe a:contains(all blogs)",
            run: "click",
        },
        {
            trigger: ":iframe .h1:contains(our latest posts)",
        },
        {
            content: "Click on the adventure tag",
            trigger: ":iframe a[href^='/blog/tag/adventure'].o_post_link_js_loaded",
            run: "click",
        },
        {
            content: "Verify we are still on the backend",
            trigger: ":iframe span:contains(adventure) i.fa-tag",
        },
    ]
);
