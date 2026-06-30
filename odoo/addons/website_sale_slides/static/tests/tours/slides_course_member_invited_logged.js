/** @odoo-module **/

import { registry } from '@web/core/registry';


registry.category('web_tour.tours').add('invited_on_payment_course_logged', {
    test: true,
    steps: () => [
{
    trigger: 'a:contains("Add to Cart")',
    content: 'Check that the course can be bought but not joined',
    run: function () {
        if (document.querySelector('.o_wslides_js_course_join_link')) {
            throw new Error('The course should not be joinable before buying');
        }
    }
}, {
    trigger: '.o_wslides_slides_list_slide:contains("Home Gardening")',
    content: 'Check that non-preview slides are not accessible',
    run: function () {
        if (this.$anchor[0].querySelector('.o_wslides_js_slides_list_slide_link')) {
            throw new Error('Invited attendee should not access non-preview slides');
        }
    }
}, {
    trigger: 'a:contains("Gardening: The Know-How")',
    content: 'Check that preview slides are accessible',
    run: function () {}
}
]});
