/** @odoo-module **/

import { registry } from "@web/core/registry";
import wsTourUtils from '@website_sale/js/tours/tour_utils';

var registerSteps = [{
    content: "Open ticket modal",
    trigger: 'button.btn-primary:contains("Register")',
}, {
    content: "Select 2 units of 'Ticket1' ticket type",
    trigger: '#o_wevent_tickets_collapse .row.o_wevent_ticket_selector[name="Ticket1"] select',
    run: 'text 2',
}, {
    content: "Select 1 unit of 'Ticket2' ticket type",
    trigger: '#o_wevent_tickets_collapse .row.o_wevent_ticket_selector[name="Ticket2"] select',
    run: 'text 1',
}, {
    content: "Click on 'Register' button",
    trigger: '#o_wevent_tickets .btn-primary:contains("Register"):not(:disabled)',
    run: 'click',
}, {
    content: "Fill attendees details",
    trigger: 'form[id="attendee_registration"] .btn[type=submit]',
    run: function () {
        $("input[name*='1-name']").val("Raoulette Poiluchette");
        $("input[name*='1-phone']").val("0456112233");
        $("input[name*='1-email']").val("raoulette@example.com");
        $("div[name*='Question1'] select[name*='1-simple_choice']").val($("select[name*='1-simple_choice'] option:contains('Q1-Answer2')").val());
        $("div[name*='Question2'] select[name*='1-simple_choice']").val($("select[name*='1-simple_choice'] option:contains('Q2-Answer1')").val());
        $("input[name*='2-name']").val("Michel Tractopelle");
        $("input[name*='2-phone']").val("0456332211");
        $("input[name*='2-email']").val("michel@example.com");
        $("div[name*='Question1'] select[name*='2-simple_choice']").val($("select[name*='2-simple_choice'] option:contains('Q1-Answer1')").val());
        $("div[name*='Question2'] select[name*='2-simple_choice']").val($("select[name*='2-simple_choice'] option:contains('Q2-Answer2')").val());
        $("input[name*='3-name']").val("Hubert Boitaclous");
        $("input[name*='3-phone']").val("0456995511");
        $("input[name*='3-email']").val("hubert@example.com");
        $("div[name*='Question1'] select[name*='3-simple_choice']").val($("select[name*='3-simple_choice'] option:contains('Q1-Answer2')").val());
        $("div[name*='Question2'] select[name*='3-simple_choice']").val($("select[name*='3-simple_choice'] option:contains('Q2-Answer2')").val());
        $("textarea[name*='question_answer']").text("Random answer from random guy");
    },
}, {
    content: "Validate attendees details",
    extra_trigger: "input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
    trigger: 'button[type=submit]',
    run: 'click',
},
wsTourUtils.fillAdressForm({
    name: "Raoulette Poiluchette",
    phone: "0456112233",
    email: "raoulette@example.com",
    street: "Cheesy Crust Street, 42",
    city: "CheeseCity",
    zip: "8888",
}),
...wsTourUtils.payWithDemo(),
];


registry.category("web_tour.tours").add('wevent_performance_register', {
    test: true,
    steps: () => [].concat(
        registerSteps,
    )
});
