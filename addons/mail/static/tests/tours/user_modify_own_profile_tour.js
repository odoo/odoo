/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * Verify that a user can modify their own profile information.
 */
tour.register('mail/static/tests/tours/user_modify_own_profile_tour.js', {
    test: true,
}, [{
    content: 'Open user account menu',
    trigger: '.o_user_menu button',
}, {
    content: "Open preferences / profile screen",
    trigger: '[data-menu=settings]',
}, {
    content: "Update the email address",
    trigger: 'div[name="email"] input',
    run: 'text updatedemail@example.com',
}, {
    content: "Save the form",
    trigger: 'button[name="preference_save"]',
}, {
    content: "Wait until the modal is closed",
    trigger: 'body:not(.modal-open)',
}]);
