/** @odoo-module **/

import slidesTourTools from '@website_slides/../tests/tours/slides_tour_tools';
import { clickOnEditAndWaitEditMode, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';
import { waitForStable } from '@web/core/macro';

/**
 * Global use case:
 * a user (website publisher) creates a course;
 * they update it;
 * they create some lessons in it;
 * they publish it;
 */
registerWebsitePreviewTour('course_publisher_standard', {
    url: '/slides',
}, () => [{
    content: 'eLearning: click on New (top-menu)',
    trigger: 'div.o_new_content_container a',
    run: "click",
}, {
    content: 'eLearning: click on New Course',
    trigger: '#o_new_content_menu_choices a:contains("Course")',
    run: "click",
}, {
    content: 'eLearning: set name',
    trigger: 'div[name="name"] input',
    run: "edit How to Déboulonnate",
}, {
    content: 'eLearning: click on tags',
    trigger: '.o_field_many2many_tags input',
    run: "edit Gard",
}, {
    content: 'eLearning: select Gardening tag',
    trigger: '.ui-autocomplete a:contains("Gardening")',
    run: "click",
}, {
    content: 'eLearning: set description',
    trigger: '.o_field_html[name="description"] .odoo-editor-editable div.o-paragraph',
    run: "editor Déboulonnate is very common at Fleurus",
}, {
    content: 'eLearning: we want reviews',
    trigger: '.o_field_boolean[name="allow_comment"] input',
    run: "click",
}, {
    content: 'eLearning: seems cool, create it',
    trigger: '.modal button:contains("Save")',
    run: "click",
},
{
    trigger: "body:not(:has(.modal))",
},
...clickOnEditAndWaitEditMode(),
{
    content: 'eLearning: double click image to edit it',
    trigger: ':iframe img.o_wslides_course_pict',
    run: 'dblclick',
}, {
    content: 'eLearning: click "Add URL" to trigger URL box',
    trigger: '.o_upload_media_url_button',
    run: "click",
}, {
    content: 'eLearning: add a bioutifoul URL',
    trigger: 'input.o_we_url_input',
    run: "edit https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/ThreeTimeAKCGoldWinnerPembrookeWelshCorgi.jpg/800px-ThreeTimeAKCGoldWinnerPembrookeWelshCorgi.jpg",
},
{
    trigger: ".o_we_url_success",
},
{
    content: 'eLearning: click "Add URL" really adding image',
    trigger: '.o_upload_media_url_button',
    run: "click",
}, {
    content: 'eLearning: is the Corgi set ?',
    trigger: ':iframe img.o_wslides_course_pict.o_modified_image_to_save[data-original-src$="GoldWinnerPembrookeWelshCorgi.jpg"][src^="data:image"]',
    run: "click",
}, {
    content: 'eLearning: save course edition',
    trigger: 'button[data-action="save"]',
    run: "click",
},
{
    trigger: ":iframe body:not(.editor_enable)", // wait for editor to close
},
{
    content: 'eLearning: course create with current member',
    trigger: ':iframe .o_wslides_js_course_join:contains("You\'re enrolled")',
}
].concat(
    slidesTourTools.addExistingCourseTag(true),
    slidesTourTools.addNewCourseTag('The Most Awesome Course', true),
    slidesTourTools.addSection('Introduction', true),
    slidesTourTools.addArticleToSection('Introduction', 'MyArticle', true),
    [{
    content: "eLearning: check editor is loaded for article",
    trigger: ':iframe body.editor_enable',
    timeout: 30000,
}, {
    content: "eLearning: save article",
    trigger: '.o_we_website_top_actions button.btn-primary:contains("Save")',
    run: "click",
},
{
    trigger: "[is-ready=true]:iframe body:not(.editor_enable)",
},
{
    trigger:
        ":iframe main:has(.o_wslides_course_nav a:contains(Déboulonnate)):has(.o_wslides_lesson_header_container:contains(completed)):has(.o_wslides_lesson_content:contains(screen to edit))",
},
{
    content: "eLearning: use breadcrumb to go back to channel",
    trigger: ':iframe .o_wslides_course_nav a:contains("Déboulonnate")[href^="/slides/how-to-deboulonnate"]',
    async run(actions) {
        await waitForStable(document, 2000);
        await actions.click();
    }
}],
    slidesTourTools.addImageToSection('Introduction', 'Overview', true),
    slidesTourTools.addPdfToSection('Introduction', 'Exercise', true),
//     [
// {
//     content: 'eLearning: move new course inside introduction',
//     trigger: 'div.o_wslides_slides_list_drag',
//     // run: 'drag_and_drop div.o_wslides_slides_list_drag ul.ui-sortable:first',
//     run: 'drag_and_drop div.o_wslides_slides_list_drag a.o_wslides_js_slide_section_add',
// }]
));
