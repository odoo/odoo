/** @odoo-module **/

import { stepUtils } from "@web_tour/tour_service/tour_utils";
import { registry } from "@web/core/registry";

/**
 * As 'hr' changes the flow a bit and displays the user preferences form in a full view instead of
 * a modal, we adapt the steps of the original tour accordingly.
 */
registry.category("web_tour.tours").get('mail/static/tests/tours/user_modify_own_profile_tour.js').steps = [{
    content: 'Open user account menu',
    trigger: '.o_user_menu button',
}, {
    content: "Open preferences / profile screen",
    trigger: '[data-menu=settings]',
}, {
    content: "Update the email address",
    trigger: 'div[name="email"] input',
    run: 'text updatedemail@example.com',
}, ...stepUtils.saveForm()];
