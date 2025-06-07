/** @odoo-module **/

import { clickOnEditAndWaitEditMode, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';
import slidesTourTools from '@website_slides/../tests/tours/slides_tour_tools';

/**
 * Global use case:
 * a user (website restricted editor) creates a course;
 * they update it;
 * they create some lessons in it;
 * they publishe it;
 */
registerWebsitePreviewTour('course_publisher', {
    // TODO: replace by getClientActionURL when it's added
    url: '/slides'
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
    trigger: "modal:not(.o_inactive_modal) div[name=name] input",
    run: "edit How to Déboulonnate",
}, {
    content: 'eLearning: click on tags',
    trigger: ".modal .o_field_many2many_tags input",
    run: "edit Gard",
}, {
    content: 'eLearning: select gardener tag',
    trigger: ".modal .ui-autocomplete a:contains(Gardener)",
    run: "click",
}, {
    content: 'eLearning: set description',
    trigger: 'modal .o_field_html[name="description"] .odoo-editor-editable p',
    run: "editor Déboulonnate is very common at Fleurus",
}, {
    content: 'eLearning: we want reviews',
    trigger: '.o_field_boolean[name="allow_comment"] input',
    run: "click",
}, {
    content: 'eLearning: seems cool, create it',
    trigger: ".modal button:contains(Save)",
    run: "click",
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
    trigger: ':iframe img.o_wslides_course_pict[data-original-src$="GoldWinnerPembrookeWelshCorgi.jpg"]',
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
    // check membership
    content: 'eLearning: course create with current member',
    trigger: ':iframe .o_wslides_js_course_join:contains("You\'re enrolled")',
}
].concat(
    slidesTourTools.addExistingCourseTag(true),
    slidesTourTools.addNewCourseTag('The Most Awesome Course', true),
    slidesTourTools.addSection('Introduction', true),
    slidesTourTools.addVideoToSection('Introduction', false, true),
    [{
    content: 'eLearning: publish newly added course',
    trigger: ':iframe span:contains("Dschinghis Khan - Dschinghis Khan (1979)")',  // wait for slide to appear
    // trigger: 'span.o_wslides_js_slide_toggle_is_preview:first',
    run() {
        document.querySelector(
            ".o_website_preview :iframe span.o_wslides_js_slide_toggle_is_preview"
        ).click();
    }
}]
//     [
// {
//     content: 'eLearning: move new course inside introduction',
//     trigger: 'div.o_wslides_slides_list_drag',
//     // run: 'drag_and_drop div.o_wslides_slides_list_drag ul.ui-sortable:first',
//     run: 'drag_and_drop div.o_wslides_slides_list_drag a.o_wslides_js_slide_section_add',
// }]
));
