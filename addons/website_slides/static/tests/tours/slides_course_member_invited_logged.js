/** @odoo-module **/

import { registry } from '@web/core/registry';


registry.category('web_tour.tours').add('invite_check_channel_preview_as_logged', {
    test: true,
    steps: () => [
{
    trigger: 'a:contains("Gardening: The Know-How")',
    content: 'Check that the previews are accessible',
    run: function () {}
}, {
    trigger: '.o_wslides_slides_list_slide:contains("Home Gardening")',
    content: 'Check that other slides are not accessible',
    run: function () {
        if (this.$anchor[0].querySelector('.o_wslides_js_slides_list_slide_link')) {
            throw new Error('Invited attendee should not see non-preview slides');
        }
    }
}, {
    trigger: 'a:contains("Join this Course")',
}, {
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    content: 'Check that user is enrolled',
    run: function () {}
}, {
    trigger: '.o_wslides_js_slides_list_slide_link:contains("Home Gardening")',
    content: 'Check that slides are now accessible',
    run: function () {}
},
]});
