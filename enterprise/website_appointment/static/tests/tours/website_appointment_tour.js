/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('website_appointment_tour', {
    url: '/odoo',
    steps: () => [
    stepUtils.showAppsMenuItem(),
    {
        content: 'Click on appointment app',
        trigger: '.o_app[data-menu-xmlid="appointment.main_menu_appointments"]',
        run: "click",
    }, {
        content: 'Click on Create button',
        trigger: '.o-kanban-button-new',
        run: "click",
    }, {
        content: 'Set name of appointment type',
        trigger: '#name_0',
        run: "edit Test",
    }, {
        content: 'Set max scheduled days',
        trigger: '#max_schedule_days_0',
        run: "edit 45",
    }, {
        content: 'Open the options tab',
        trigger: 'a[name="options"]',
        run: "click",
    }, {
        content: 'Checked the allow_guests',
        trigger: '#allow_guests_0',
        run: "click",
    }, {
        content: 'Save appointment type',
        trigger: '.o_form_button_save',
        run: "click",
    }, {
        content: 'Go to the front end',
        trigger: "button[name=action_customer_preview]:enabled",
        run: "click",
        expectUnloadPage: true,
    }, {
        content: 'Click on first date available',
        trigger: '.o_slots_list > div > button',
        run: "click",
        expectUnloadPage: true,
    }, {
        content: 'Fill tel field',
        trigger: 'input[name="phone"]',
        run: "edit 0123456789",
    }, {
        content: 'Click on the add guest link',
        trigger: 'button.btn-link',
        run: "click",
    }, {
        content: 'Enter the emails of the guests',
        trigger: '#o_appointment_input_guest_emails',
        run:()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'test1@gmail.com\r\nportal@example.com\r\naaaa'
        }
    }, {
        content: 'Click on the add guest button',
        trigger: '.o_appointment_form_confirm_btn',
        run: "click",
    }, {
        content: 'Check the error msg',
        trigger: '.o_appointment_error_text:contains("Invalid Email")',
    }, {
        content: 'Removing the Invalid Email from the text area',
        trigger: '#o_appointment_input_guest_emails',
        run:()=>{
            document.querySelector('#o_appointment_input_guest_emails').value =
                '"Raoul" <hello@gmail.com>\r\ntest1@gmail.com\r\nnew_zeadland2@test.example.com\r\n\r\nportal@example.com\r\napt_manager@test.example.com'
        }
    }, {
        content: 'Confirm the appointment',
        trigger: '.o_appointment_form_confirm_btn',
        run: "click",
        expectUnloadPage: true,
    }, {
        trigger: 'div:contains("test1@gmail.com")',
    }, {
        trigger: 'div:contains("Portal User")',
    }, {
        trigger: 'div:contains("new_zeadland2@test.example.com")',
    }, {
        trigger: 'div:contains("Raoul")',
    }, {
        trigger: '.o_appointment_guest_addition_open',
        content: 'Adding the guest at the validation page',
        run: "click",
    }, {
        content: 'Check the email validation on validation page',
        trigger: '#o_appointment_input_guest_emails',
        run:()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'test2@gmail.com\r\nabc@gmail.com def@gmail.example.com\r\ntest1tttt'
        }
    }, {
        content: 'Click on the add guest button',
        trigger: '.o_appointment_guest_add',
        run: "click",
    }, {
        content: 'Checking the error msg on the validation page',
        trigger: '.o_appointment_error_text:contains("Invalid Email")',
    }, {
        content: 'Remove the invalid email from the input',
        trigger: '#o_appointment_input_guest_emails',
        run: ()=>{
            document.querySelector('#o_appointment_input_guest_emails').value = 'test2@gmail.com\r\nabc@gmail.com def@gmail.example.com\r\ntest1@gmail.com'
        },
    }, {
        content: 'Click on the add guest button',
        trigger: '.o_appointment_guest_add',
        run: "click",
        expectUnloadPage: true,
    }, {
        trigger: 'div:contains("test2@gmail.com")',
    }, {
        trigger: 'div:contains("abc@gmail.com")',
    }, {
        trigger: 'div:contains("def@gmail.example.com")',
    },
]});
