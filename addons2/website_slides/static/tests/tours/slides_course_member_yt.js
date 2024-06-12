/** @odoo-module **/

import { registry } from "@web/core/registry";

function patchFullScreen(){
    /**
     * Alter this method for test purposes.
     * This will make the video start at 10 minutes.
     * As it lasts 10min24s, it will mark it as completed immediately.
    */
    const FullScreen = odoo.loader.modules.get('@website_slides/js/slides_course_fullscreen_player')[Symbol.for("default")];
    FullScreen.include({
        _renderSlide: function () {

            var slide = this.get('slide');
            slide.embedUrl += '&start=260';
            this.set('slide', slide);

            return this._super.call(this, arguments);
        }
    });
}


/**
 * Global use case:
 * an user (either employee, website restricted editor or portal) joins a public
    course;
 * they have access to the full course content when they are a member of the
    course;
 * they use fullscreen player to complete the course;
 * they rate the course;
 */
registry.category("web_tour.tours").add('course_member_youtube', {
    url: '/slides',
    test: true,
    steps: () => [
{
    content: "Patching FullScreen",
    trigger: 'body',
    run: function() {
        patchFullScreen()
    }
},
// eLearning: go on /all, find free course and join it
{
    trigger: 'a.o_wslides_home_all_slides'
}, {
    trigger: 'a:contains("Choose your wood")'
}, {
    trigger: 'a:contains("Join this Course")'
}, {
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {} // check membership
}, {
    trigger: 'a:contains("Comparing Hardness of Wood Species")',
},  {
    trigger: '.o_wslides_progress_percentage:contains("50")',
    run: function () {} // check progression
}, {
    trigger: '.o_wslides_fs_slide_name:contains("Wood Bending With Steam Box")',
}, {
    trigger: '.player',
    run: function () {} // check player loading
}, {
    trigger: '.o_wslides_fs_sidebar_section_slides li:contains("Wood Bending With Steam Box") .o_wslides_slide_completed',
    run: function () {} // check that video slide is marked as 'done'
}, {
    trigger: '.o_wslides_channel_completion_completed:contains(Completed)',
    run: function () {} // check progression
}, {
    trigger: 'a:contains("Back to course")'
}
]});
