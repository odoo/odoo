import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

/**
 * @param {string} eventName The name of the event for which
 * registration is requested.
 */
const goToRegistrationSteps = function (eventName) {
    return [
        stepUtils.goToUrl("/event"),
        {
            content: `Click on ${eventName}`,
            trigger: `article:contains(${eventName})`,
            run: "click",
        },
        {
            content: "Click on Register modal tickets button",
            trigger: "button:contains(Register)",
            run: "click",
        },
    ]
}

const confirmRegistrationSteps = [
    {
        content: "Click on Register to submit registrations",
        trigger: ".modal button[type='submit']:enabled",
        run: "click",
    },
    {
        content: "Wait for confirmation",
        trigger: ".o_wereg_confirmed, .oe_cart",
    },
]

registry.category("web_tour.tours").add("website_event_registrations", {
    steps: () => [].concat(
        // Test registrations without tickets and without the attendee details form.
        goToRegistrationSteps("Event No tickets And Without Questions"),
        [
            {
                content: "Select 4 registrations",
                trigger: "div.o_wevent_registration_single select.form-select",
                run: "select 4",
            },
        ],
        confirmRegistrationSteps,
        // Test registrations without tickets and with the attendee details form.
        goToRegistrationSteps("Event No tickets And With Questions"),
        [
            {
                content: "Click on Register button to order 1 registration",
                trigger: "div.modal-footer button:contains(Register)",
                run: "click",
            },
            {
                content: "Wait the modal is shown before continue",
                trigger: ".modal.modal_shown.show form[id=attendee_registration]",
            },
            {
                trigger: "div:contains(Ticket #1).modal-body input[name*='email']",
                run: "edit attendee-no-tickets@gmail.com",
            },
        ],
        confirmRegistrationSteps,
        // Test registrations without the attendee details form.
        goToRegistrationSteps("Event Without Questions"),
        [
            {
                content: "Check Register button is disabled when no ticket selected",
                trigger: "#registration_form button[type='submit']:disabled",
            },
            {
                content: "Select 3 'Regular' tickets",
                trigger: "div.o_wevent_ticket_selector:contains(Regular) select.form-select",
                run: "select 3",
            },
            {
                content: "Select 2 'VIP' tickets",
                trigger: "div.o_wevent_ticket_selector:contains(VIP) select.form-select",
                run: "select 2",
            },
        ],
        confirmRegistrationSteps,
        // Test registrations with the attendee details form.
        goToRegistrationSteps("Event With Questions"),
        [
            {
                content: "Select 1 'Regular' tickets",
                trigger: "div.o_wevent_ticket_selector:contains(Regular) select.form-select",
                run: "select 1",
            },
            {
                content: "Select 2 'VIP' tickets",
                trigger: "div.o_wevent_ticket_selector:contains(VIP) select.form-select",
                run: "select 1",
            },
            {
                content: "Click on Register (to fill tickets data) button",
                trigger: "div.modal-footer button:contains(Register)",
                run: "click",
            },
            {
                content: "Wait the modal is shown before continue",
                trigger: ".modal.modal_shown.show form[id=attendee_registration]",
            },
            {
                trigger: "div.o_wevent_registration_question_global select[name*='0-simple_choice']",
                run: "selectByLabel A friend",
            },
            {
                trigger: "div:contains(Ticket #1).modal-body input[name*='name']",
                run: "edit Attendee A",
            },
            {
                trigger: "div:contains(Ticket #1).modal-body input[name*='email']",
                run: "edit attendee-a@gmail.com",
            },
            {
                trigger: "div:contains(Ticket #1).modal-body input[name*='phone']",
                run: "edit +32499123456",
            },
            {
                trigger: "div:contains(Ticket #1).modal-body select[name*='1-simple_choice']",
                run: "selectByLabel Vegetarian",
            },
            {
                trigger: "div:contains(Ticket #1).modal-body textarea[name*='1-text_box']",
                run: "edit Fish and Nuts",
            },
            {
                trigger: "div:contains(Ticket #2).modal-body input[name*='name']",
                run: "edit Attendee B",
            },
            {
                trigger: "div:contains(Ticket #2).modal-body input[name*='email']",
                run: "edit attendee-b@gmail.com",
            },
            {
                trigger: "div:contains(Ticket #2).modal-body input[name*='company_name']",
                run: "edit My Company",
            },
            {
                trigger: "div:contains(Ticket #2).modal-body select[name*='2-simple_choice']",
                run: "selectByLabel Pastafarian",
            },
        ],
        confirmRegistrationSteps,
    )
});
