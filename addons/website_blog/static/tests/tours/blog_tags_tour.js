/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * Makes sure that blog tags can be created and removed.
 */
tour.register('blog_tags', {
    test: true,
    url: '/blog',
}, [{
        content: "Go to first blog",
        trigger: "article[name=blog_post] a",
    }, {
        content: "Edit blog post",
        trigger: "a[data-action=edit]",
        extra_trigger: "section#o_wblog_post_main",
    }, {
        content: "Open tag dropdown",
        trigger: "we-customizeblock-option:contains(Tags) we-toggler",
    }, {
        content: "Enter tag name",
        trigger: "we-customizeblock-option:contains(Tags) we-selection-items .o_we_m2o_create input",
        run: "text testtag",
    }, {
        content: "Click Create",
        trigger: "we-customizeblock-option:contains(Tags) we-selection-items .o_we_m2o_create we-button",
    }, {
        content: "Verify tag appears in options",
        trigger: "we-customizeblock-option:contains(Tags) we-list input[data-name=testtag]",
        run: () => {}, // it's a check
    }, {
        content: "Click Save",
        trigger: "button[data-action=save]",
    }, {
        content: "Verify tag appears in blog post",
        trigger: "#o_wblog_post_content .badge:contains(testtag)",
        run: () => {}, // it's a check
    }, {
        content: "Edit blog post",
        trigger: "a[data-action=edit]",
    }, {
        content: "Remove tag",
        trigger: "we-customizeblock-option:contains(Tags) we-list tr:has(input[data-name=testtag]) we-button.fa-minus",
    }, {
        content: "Verify tag does not appear in options anymore",
        trigger: "we-customizeblock-option:contains(Tags) we-list:not(:has(input[data-name=testtag]))",
        run: () => {}, // it's a check
    }, {
        content: "Click Save",
        trigger: "button[data-action=save]",
    }, {
        content: "Verify tag does not appear in blog post anymore",
        trigger: "#o_wblog_post_content div:has(.badge):not(:contains(testtag))",
        run: () => {}, // it's a check
    }]
);
