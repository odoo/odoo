odoo.define('website_slides.tours.slide.course.member', function (require) {
'use strict';

var tour = require('web_tour.tour');
var FullScreen = require('website_slides.fullscreen');

/**
 * Alter this method for test purposes.
 * This will make the video start at 10 minutes.
 * As it lasts 10min24s, it will mark it as completed immediately.
 */
FullScreen.include({
    _renderSlide: function () {

        var slide = this.get('slide');
        slide.embedUrl += '&start=600';
        this.set('slide', slide);

        return this._super.call(this, arguments);
    }
});

/**
 * Global use case:
 * - student (= demo user) goes on channel_0 (Basics of Gardening)
 * - clicks on slide_slide_demo_0_0 (Know-How) which is free
 * - clicks on "join course"
 * - has access to all content
 * - completes the course
 */
tour.register('course_tour', {
    url: '/slides',
    test: true
}, [{
    trigger: 'a:contains("Basics of Gardening")'
}, {
    trigger: '.o_wslides_slides_list_slide:contains("Gardening: The Know-How")',
    run: function () {} // check that the previewable slide is displayed
}, {
    trigger: 'a:contains("Join Course")'
}, {
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {} // check membership
}, {
    trigger: 'a:contains("Gardening: The Know-How")',
}, {
    trigger: '.o_wslides_fs_sidebar_list_item div:contains("Home Gardening")'
}, {
    trigger: '.o_wslides_fs_sidebar_header',
    run: function () {
        // check navigation with arrow keys
        var event = jQuery.Event("keydown");
        event.key = "ArrowLeft";
        // go back once
        $(document).trigger(event);
        // check that it selected the previous tab
        if ($('.o_wslides_fs_sidebar_list_item.active:contains("Gardening: The Know-How")').length === 0) {
            return;
        }

        event.key = "ArrowRight";
        // forward twice
        $(document).trigger(event);
        $(document).trigger(event);
        // check that it selected the next/next tab
        if ($('.o_wslides_fs_sidebar_list_item.active:contains("Mighty Carrots")').length === 0) {
            return;
        }

        // getting here means that navigation worked
        $('.o_wslides_fs_sidebar_header').addClass('navigation-success');
    }
}, {
    trigger: '.o_wslides_fs_sidebar_header.navigation-success',
    run: function () {} // check that previous step succeeded
}, {
    trigger: '.o_wslides_fs_sidebar_list_item div:contains("How to Grow and Harvest The Best Strawberries | Gardening Tips and Tricks")'
}, {
    trigger: '.player',
    run: function () {} // check player loading
}, {
    trigger: '.o_wslides_fs_sidebar_section_slides li:contains("How to Grow and Harvest The Best Strawberries | Gardening Tips and Tricks") .o_wslides_slide_completed',
    run: function () {} // check that video slide is marked as 'done'
}, {
    trigger: '.o_wslides_progress_percentage:contains("100")',
    run: function () {} // check progression
}, {
    trigger: '.o_wslides_fs_sidebar_list_item div:contains("A little chat with Harry Potted") .o_wslides_fs_slide_quiz'
}, {
    trigger: '.o_wslides_js_lesson_quiz_question:first .list-group a:first'
}, {
    trigger: '.o_wslides_js_lesson_quiz_question:last .list-group a:first'
}, {
    trigger: '.o_wslides_js_lesson_quiz_submit'
}, {
    trigger: '.o_wslides_quiz_btn'
}, {
    trigger: '.o_wslides_fs_sidebar_section_slides li:contains("A little chat with Harry Potted") .o_wslides_slide_completed',
    run: function () {} // check that webpage slide is marked as 'done'
}, {
    trigger: '.o_wslides_fs_sidebar_list_item div:contains("3 Main Methodologies")'
}, {
    trigger: '.o_wslides_progress_percentage:contains("100")',
    run: function () {} // check completion
}, {
    trigger: '.o_wslides_slide_fs_header a:contains("Back to course")'
}, {
    trigger: '.o_wslides_course_nav a:contains("Home")'
}, {
    trigger: 'div:contains("Taking care of Trees") span:contains("Completed")',
    run: function () {} // check that the course is marked as completed
}
]);

});
