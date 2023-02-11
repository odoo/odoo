/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * Global use case:
 * - a user (website publisher) lands on the fullscreen view of a course ;
 * - he clicks on the website editor "Edit" button ;
 * - he is redirected to the non-fullscreen view with the editor opened.
 *
 * This tour tests a fix made when editing a course in fullscreen view.
 * See "Fullscreen#_onWebEditorClick" for more information.
 *
 */
tour.register('full_screen_web_editor', {
    url: '/slides',
    test: true
}, [{
    // open to the course
    trigger: 'a:contains("Basics of Gardening")'
}, {
    // click on a slide to open the fullscreen view
    trigger: 'a.o_wslides_js_slides_list_slide_link:contains("Home Gardening")'
}, {
    trigger: '.o_wslides_fs_main',
    run: function () {} // check we land on the fullscreen view
}, {
    // click on the main "Edit" button to open the web editor
    trigger: '#edit-page-menu a[data-action="edit"]',
}, {
    trigger: '.o_wslides_lesson_main',
    run: function () {} // check we are redirected on the detailed view
}, {
    trigger: 'body.editor_enable',
    run: function () {} // check the editor is automatically opened on the detailed view
}]);
