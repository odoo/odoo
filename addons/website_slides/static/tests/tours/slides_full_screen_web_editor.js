/** @odoo-module **/

import { clickOnEditAndWaitEditMode, registerWebsitePreviewTour } from '@website/js/tours/tour_utils';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

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
registerWebsitePreviewTour('full_screen_web_editor', {
    url: '/slides',
}, () => [
    stepUtils.waitIframeIsReady(),
    {
    // open to the course
    trigger: ':iframe a:contains("Basics of Gardening")',
    run: "click",
}, {
    // click on a slide to open the fullscreen view
    trigger: ':iframe a.o_wslides_js_slides_list_slide_link:contains("Home Gardening")[href*="fullscreen=1"]',
    run: "click",
}, {
    // check we land on the fullscreen view
    trigger: ':iframe .o_wslides_fs_main',
},
...clickOnEditAndWaitEditMode()
, {
    // check we are redirected on the detailed view
    trigger: ':iframe .o_wslides_lesson_main',
}]);
