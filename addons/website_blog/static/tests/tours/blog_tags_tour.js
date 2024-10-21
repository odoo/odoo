/** @odoo-module **/

import {
    clickOnEditAndWaitEditMode,
    clickOnSave,
    clickOnSnippet,
    registerWebsitePreviewTour,
} from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";


/**
 * Makes sure that blog tags can be created and removed.
 */
registerWebsitePreviewTour('blog_tags', {
    url: '/blog',
}, () => [
    stepUtils.waitIframeIsReady(),
    {
        content: "Go to the 'Post Test' blog",
        trigger: ":iframe article[name=blog_post] a:contains('Post Test')",
        run: "click",
    },
    ...clickOnEditAndWaitEditMode(),
    ...clickOnSnippet('#o_wblog_post_top .o_wblog_post_page_cover'),
    {
        content: "Open tag dropdown",
        trigger: "we-customizeblock-option:contains(Tags) .o_we_m2m we-toggler",
        run: "click",
    }, {
        content: "Enter tag name",
        trigger: "we-customizeblock-option:contains(Tags) we-selection-items .o_we_m2o_create input",
        run: "edit testtag",
    }, {
        content: "Click Create",
        trigger: "we-customizeblock-option:contains(Tags) we-selection-items .o_we_m2o_create we-button",
        run: "click",
    }, {
        content: "Verify tag appears in options",
        trigger: "we-customizeblock-option:contains(Tags) we-list input[data-name=testtag]",
    },
    ...clickOnSave(),
    {
        content: "Verify tag appears in blog post",
        trigger: ":iframe #o_wblog_post_content .badge:contains(testtag)",
    },
    ...clickOnEditAndWaitEditMode(),
    ...clickOnSnippet('#o_wblog_post_top .o_wblog_post_page_cover'),
    {
        content: "Remove tag",
        trigger: "we-customizeblock-option:contains(Tags) we-list tr:has(input[data-name=testtag]) we-button.fa-minus",
        run: "click",
    }, {
        content: "Verify tag does not appear in options anymore",
        trigger: "we-customizeblock-option:contains(Tags) we-list:not(:has(input[data-name=testtag]))",
    },
    ...clickOnSave(),
    {
        content: "Verify tag does not appear in blog post anymore",
        trigger: ":iframe #o_wblog_post_content div:has(.badge):not(:contains(testtag))",
    }, {
        content: "Go back to /blog",
        trigger: ":iframe .top_menu a[href='/blog'] span",
        run: "click",
    }, {
        content: "Click on the adventure tag",
        trigger: ":iframe a[href^='/blog/tag/adventure']",
        run: "click",
    }, {
        content: "Verify we are still on the backend",
        trigger: ":iframe span:contains(adventure) i.fa-tag",
    }]
);
