odoo.define('website_slides.tour.slide.course.member.youtube', function (require) {
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
        slide.embedUrl += '&start=260';
        this.set('slide', slide);

        return this._super.call(this, arguments);
    }
});

/**
 * Global use case:
 * an user (either employee, website publisher or portal) joins a public
    course;
 * he has access to the full course content when he's a member of the
    course;
 * he uses fullscreen player to complete the course;
 * he rates the course;
 */
tour.register('course_member_youtube', {
    url: '/slides',
    test: true
}, [
// eLearning: go on /all, find free course and join it
{
    trigger: 'a.o_wslides_home_all_slides'
}, {
    trigger: 'a:contains("Choose your wood")'
}, {
    trigger: 'a:contains("Join Course")'
}, {
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {} // check membership
}, {
    trigger: 'a:contains("Comparing Hardness of Wood Species")',
},  {
    trigger: '.o_wslides_progress_percentage:contains("50")',
    run: function () {} // check progression
}, {
    trigger: 'a:contains("Wood Bending With Steam Box")',
}, {
    trigger: '.player',
    run: function () {} // check player loading
}, {
    trigger: '.o_wslides_fs_sidebar_section_slides li:contains("Wood Bending With Steam Box") .o_wslides_slide_completed',
    run: function () {} // check that video slide is marked as 'done'
}, {
    trigger: '.o_wslides_progress_percentage:contains("100")',
    run: function () {} // check progression
}, {
    trigger: 'a:contains("Back to course")'
}
]);

});
