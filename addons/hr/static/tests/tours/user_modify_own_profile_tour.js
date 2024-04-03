/** @odoo-module **/

import tour from 'web_tour.tour';

/**
 * As 'hr' changes the flow a bit and displays the user preferences form in a full view instead of
 * a modal, we adapt the steps of the original tour accordingly.
 */
tour.tours['mail/static/tests/tours/user_modify_own_profile_tour.js'].steps = [{
    content: 'Open user account menu',
    trigger: '.o_user_menu button',
}, {
    content: "Open preferences / profile screen",
    trigger: '[data-menu=settings]',
}, {
    content: "Update the email address",
    trigger: 'div[name="email"] input',
    run: 'text updatedemail@example.com',
}, ...tour.stepUtils.saveForm()];
