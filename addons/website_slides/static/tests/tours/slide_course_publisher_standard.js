/** @odoo-module **/

import slidesTourTools from '@website_slides/../tests/tours/slides_tour_tools';
import wTourUtils from 'website.tour_utils';

/**
 * Global use case:
 * a user (website publisher) creates a course;
 * they update it;
 * they create some lessons in it;
 * they publish it;
 */
wTourUtils.registerWebsitePreviewTour('course_publisher_standard', {
    url: '/slides',
    test: true,
}, [{
    content: 'eLearning: click on New (top-menu)',
    trigger: 'div.o_new_content_container a'
}, {
    content: 'eLearning: click on New Course',
    trigger: '#o_new_content_menu_choices a:contains("Course")'
}, {
    content: 'eLearning: set name',
    trigger: 'div[name="name"] input',
    run: 'text How to Déboulonnate',
}, {
    content: 'eLearning: click on tags',
    trigger: '.o_field_many2many_tags input',
    run: 'text Gard',
}, {
    content: 'eLearning: select gardener tag',
    trigger: '.ui-autocomplete a:contains("Gardener")',
    in_modal: false,
}, {
    content: 'eLearning: set description',
    trigger: '.o_field_html[name="description"]',
    run: 'text Déboulonnate is very common at Fleurus',
}, {
    content: 'eLearning: we want reviews',
    trigger: '.o_field_boolean[name="allow_comment"] input',
}, {
    content: 'eLearning: seems cool, create it',
    trigger: 'button:contains("Save")',
},
...wTourUtils.clickOnEditAndWaitEditMode(),
{
    content: 'eLearning: double click image to edit it',
    trigger: 'iframe img.o_wslides_course_pict',
    run: 'dblclick',
}, {
    content: 'eLearning: click "Add URL" to trigger URL box',
    trigger: '.o_upload_media_url_button',
}, {
    content: 'eLearning: add a bioutifoul URL',
    trigger: 'input.o_we_url_input',
    run: 'text https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ThreeTimeAKCGoldWinnerPembrookeWelshCorgi.jpg/800px-ThreeTimeAKCGoldWinnerPembrookeWelshCorgi.jpg'
}, {
    content: 'eLearning: click "Add URL" really adding image',
    trigger: '.o_upload_media_url_button',
    extra_trigger: '.o_we_url_success',
}, {
    content: 'eLearning: is the Corgi set ?',
    trigger: 'iframe img.o_wslides_course_pict',
    run: function () {
        const $imgCorgi = $('.o_website_preview iframe').contents().find('img.o_wslides_course_pict');
        const expectedImageUrlRegex=/GoldWinnerPembrookeWelshCorgi.jpg/;
        if (expectedImageUrlRegex.test($imgCorgi.attr('src'))) {
            $imgCorgi.addClass('o_wslides_tour_success');
        }
    },
}, {
    content: 'eLearning: the Corgi is set !',
    trigger: 'iframe img.o_wslides_course_pict.o_wslides_tour_success',
}, {
    content: 'eLearning: save course edition',
    trigger: 'button[data-action="save"]',
}, {
    content: 'eLearning: course create with current member',
    extra_trigger: 'iframe body:not(.editor_enable)',  // wait for editor to close
    trigger: 'iframe .o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {} // check membership
}
].concat(
    slidesTourTools.addExistingCourseTag(true),
    slidesTourTools.addNewCourseTag('The Most Awesome Course', true),
    slidesTourTools.addSection('Introduction', true),
    slidesTourTools.addArticleToSection('Introduction', 'MyArticle', true),
    [{
    content: "eLearning: check editor is loaded for article",
    trigger: 'iframe body.editor_enable',
    timeout: 30000,
    run: () => null, // it's a check
}, {
    content: "eLearning: save article",
    trigger: '.o_we_website_top_actions button.btn-primary:contains("Save")',
}, {
    content: "eLearning: use breadcrumb to go back to channel",
    trigger: 'iframe .o_wslides_course_nav a:contains("Déboulonnate")',
}]
//     [
// {
//     content: 'eLearning: move new course inside introduction',
//     trigger: 'div.o_wslides_slides_list_drag',
//     // run: 'drag_and_drop div.o_wslides_slides_list_drag ul.ui-sortable:first',
//     run: 'drag_and_drop div.o_wslides_slides_list_drag a.o_wslides_js_slide_section_add',
// }]
));
