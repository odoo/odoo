/** @odoo-module **/

import { registry } from '@web/core/registry';


registry.category('web_tour.tours').add('invite_check_channel_preview_as_public', {
    test: true,
    steps: () => [
{
    trigger: '.o_wslides_identification_banner',
    content: 'Check that there is an identification banner',
    run: function () {}
}, {
    trigger: '.o_wslides_slides_list_slide:contains("Gardening: The Know-How")',
    run: function () {
        if (this.$anchor[0].querySelector('.o_wslides_js_slides_list_slide_link')) {
            throw new Error('The preview should not allow the public user to browse slides');
        }
    }
}, {
    trigger: 'a:contains("Join this Course")',
}, {
    trigger: 'a:contains("login")',
}, {
    trigger: 'input[id="password"]',
    run: 'text portal',
}, {
    trigger: 'button:contains("Log in")',
}, {
    trigger: 'a:contains("Join this Course")',
}, {
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    content: 'Check that user is enrolled',
    run: function () {}
}, {
    trigger: '.o_wslides_js_slides_list_slide_link:contains("Gardening: The Know-How")',
    content: 'Check that slides are now accessible',
    run: function () {}
}
]});
