/** @odoo-module **/

import { queryOne } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

var registerSteps = [{
    content: "Open ticket modal",
    trigger: 'button.btn-primary:contains("Register")',
    run: "click",
}, {
    content: "Select 2 units of 'Ticket1' ticket type",
    trigger: '#o_wevent_tickets_collapse .row.o_wevent_ticket_selector[name="Ticket1"] select',
    run: "select 2",
}, {
    content: "Select 1 unit of 'Ticket2' ticket type",
    trigger: '#o_wevent_tickets_collapse .row.o_wevent_ticket_selector[name="Ticket2"] select',
    run: "select 1",
}, {
    content: "Click on 'Register' button",
    trigger: '#o_wevent_tickets .btn-primary:contains("Register"):not(:disabled)',
    run: 'click',
}, {
    content: "Fill attendees details",
    trigger: 'form[id="attendee_registration"] .btn[type=submit]',
    run: function () {
            document.querySelector("input[name*='1-name']").value = "Raoulette Poiluchette";
            document.querySelector("input[name*='1-phone']").value = "0456112233";
            document.querySelector("input[name*='1-email']").value = "raoulette@example.com";
            document.querySelector("div[name*='Question1'] select[name*='1-simple_choice']").value =
                queryOne("select[name*='1-simple_choice'] option:contains('Q1-Answer2')").value;
            document.querySelector("div[name*='Question2'] select[name*='1-simple_choice']").value =
                queryOne("select[name*='1-simple_choice'] option:contains('Q2-Answer1')").value;
            document.querySelector("input[name*='2-name']").value = "Michel Tractopelle";
            document.querySelector("input[name*='2-phone']").value = "0456332211";
            document.querySelector("input[name*='2-email']").value = "michel@example.com";
            document.querySelector("div[name*='Question1'] select[name*='2-simple_choice']").value =
                queryOne("select[name*='2-simple_choice'] option:contains('Q1-Answer1')").value;
            document.querySelector("div[name*='Question2'] select[name*='2-simple_choice']").value =
                queryOne("select[name*='2-simple_choice'] option:contains('Q2-Answer2')").value;
            document.querySelector("input[name*='3-name']").value = "Hubert Boitaclous";
            document.querySelector("input[name*='3-phone']").value = "0456995511";
            document.querySelector("input[name*='3-email']").value = "hubert@example.com";
            document.querySelector("div[name*='Question1'] select[name*='3-simple_choice']").value =
                queryOne("select[name*='3-simple_choice'] option:contains('Q1-Answer2')").value;
            document.querySelector("div[name*='Question2'] select[name*='3-simple_choice']").value =
                queryOne("select[name*='3-simple_choice'] option:contains('Q2-Answer2')").value;
            document.querySelector("textarea[name*='question_answer']").textContent =
                "Random answer from random guy";
    },
},
{
    trigger: "input[name*='1-name'], input[name*='2-name'], input[name*='3-name']",
},
{
    content: "Validate attendees details",
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
    steps: () => [].concat(
        registerSteps,
    )
});
