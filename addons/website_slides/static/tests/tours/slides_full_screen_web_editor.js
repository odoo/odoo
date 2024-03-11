/** @odoo-module **/

import wTourUtils from 'website.tour_utils';

/**
 * Global use case:
 * - a user (website restricted editor) lands on the fullscreen view of a course ;
 * - they click on the website editor "Edit" button ;
 * - they are redirected to the non-fullscreen view with the editor opened.
 *
 * This tour tests a fix made when editing a course in fullscreen view.
 * See "Fullscreen#_onWebEditorClick" for more information.
 *
 */
 wTourUtils.registerWebsitePreviewTour('full_screen_web_editor', {
    url: '/slides',
    test: true,
}, [{
    // open to the course
    trigger: 'iframe a:contains("Basics of Gardening")'
}, {
    // click on a slide to open the fullscreen view
    trigger: 'iframe a.o_wslides_js_slides_list_slide_link:contains("Home Gardening")'
}, {
    trigger: 'iframe .o_wslides_fs_main',
    run: function () {} // check we land on the fullscreen view
},
...wTourUtils.clickOnEditAndWaitEditMode()
, {
    trigger: 'iframe .o_wslides_lesson_main',
    run: function () {} // check we are redirected on the detailed view
}]);
