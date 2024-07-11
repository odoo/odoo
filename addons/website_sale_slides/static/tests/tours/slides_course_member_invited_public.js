/** @odoo-module **/

import { registry } from '@web/core/registry';


registry.category('web_tour.tours').add('invited_on_payment_course_public', {
    test: true,
    steps: () => [
{
    trigger: '.o_wslides_identification_banner a:contains("Log in")',
    content: 'Check that there is an identification banner',
    run: function () {}
}, {
    trigger: '.o_wslides_js_course_join a:contains("Log in")',
    run: function () {
        if (document.querySelector('.o_wslides_js_course_join #add_to_cart')) {
            throw new Error('The course should not be buyable before logging in');
        }
    }
}, {
    trigger: '.o_wslides_slides_list_slide:contains("Gardening: The Know-How")',
    run: function () {
        if (this.$anchor[0].querySelector('.o_wslides_js_slides_list_slide_link')) {
            throw new Error('Invited attendee should not access slides, even previews');
        }
    }
}, {
    trigger: 'a:contains("Log in")',
}, {
    trigger: 'input[id="password"]',
    run: 'text portal',
}, {
    trigger: 'button:contains("Log in")',
}, {
    trigger: 'a:contains("Gardening: The Know-How")',
    content: 'Check that preview slides are now accessible',
    run: function () {}
}, {
    trigger: '.o_wslides_js_course_join:contains("Add to Cart")',
    content: 'Check that the course can now be bought',
    run: function () {}
}
]});
