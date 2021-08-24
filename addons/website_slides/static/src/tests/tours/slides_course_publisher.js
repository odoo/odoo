/** @odoo-module **/

import tour from 'web_tour.tour';
import slidesTourTools from '@website_slides/tests/tours/slides_tour_tools';

/**
 * Global use case:
 * a user (website publisher) creates a course;
 * he updates it;
 * he creates some lessons in it;
 * he publishes it;
 */
tour.register('course_publisher', {
    url: '/slides',
    test: true
}, [{
    content: 'eLearning: click on New (top-menu)',
    trigger: 'li.o_new_content_menu a'
}, {
    content: 'eLearning: click on New Course',
    trigger: 'a:contains("Course")'
}, {
    content: 'eLearning: set name',
    trigger: 'input[name="name"]',
    run: 'text How to Déboulonnate',
}, {
    content: 'eLearning: click on tags',
    trigger: 'ul.select2-choices:first',
}, {
    content: 'eLearning: select gardener tag',
    trigger: 'div.select2-result-label:contains("Gardener")',
    in_modal: false,
}, {
    content: 'eLearning: set description',
    trigger: 'input[name="description"]',
    run: 'text Déboulonnate is very common at Fleurus',
}, {
    content: 'eLearning: we want reviews',
    trigger: 'input[name="allow_comment"]',
}, {
    content: 'eLearning: seems cool, create it',
    trigger: 'button:contains("Create")',
}, {
    content: 'eLearning: launch course edition',
    trigger: 'li[id="edit-page-menu"] a',
}, {
    content: 'eLearning: double click image to edit it',
    trigger: 'img.o_wslides_course_pict',
    run: 'dblclick',
}, {
    content: 'eLearning: click pâtissière',
    trigger: 'img[title="s_company_team_image_4.png"]',
}, {
    content: 'eLearning: is the pâtissière set ?',
    trigger: 'img.o_wslides_course_pict',
    run: function () {
        if ($('img.o_wslides_course_pict').attr('src').endsWith('s_team_member_4.png')) {
            $('img.o_wslides_course_pict').addClass('o_wslides_tour_success');
        }
    },
}, {
    content: 'eLearning: the pâtissière is set !',
    trigger: 'img.o_wslides_course_pict.o_wslides_tour_success',
}, {
    content: 'eLearning: save course edition',
    trigger: 'button[data-action="save"]',
}, {
    content: 'eLearning: course create with current member',
    extra_trigger: 'body:not(.editor_enable)',  // wait for editor to close
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {} // check membership
}
].concat(
    slidesTourTools.addExistingCourseTag(),
    slidesTourTools.addNewCourseTag('The Most Awesome Course'),
    slidesTourTools.addSection('Introduction'),
    slidesTourTools.addVideoToSection('Introduction'),
    [{
    content: 'eLearning: publish newly added course',
    trigger: 'span:contains("Dschinghis Khan - Moskau 1979")',  // wait for slide to appear
    // trigger: 'span.o_wslides_js_slide_toggle_is_preview:first',
    run: function () {
        $('span.o_wslides_js_slide_toggle_is_preview:first').click();
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
