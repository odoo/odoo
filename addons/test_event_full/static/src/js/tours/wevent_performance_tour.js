import { registry } from "@web/core/registry";
import * as wsTourUtils from '@website_sale/js/tours/tour_utils';

var registerSteps = [{
    content: "Open ticket modal",
    trigger: 'button.btn-primary:contains("Register")',
    run: "click",
}, {
    content: "Add 2 units of 'Ticket1' ticket type by clicking the '+' button",
    trigger: 'button[data-increment-type*="plus"]',
    run: "dblclick",
}, {
    content: "Edit 1 unit of 'Ticket2' ticket type",
    trigger: '.modal input:eq(2)',
    run: "edit 1",
}, {
    content: "Click on 'Register' button",
    trigger: '#o_wevent_tickets .btn-primary:contains("Register"):not(:disabled)',
    run: 'click',
}, {
    content: "Choose the 'Q1-Answer2' answer of the 'Question1' for the first ticket",
    trigger: 'select[name*="1-simple_choice"]',
    run: "selectByIndex 2",
}, {
    content: "Choose the 'Q2-Answer1' answer of the 'Question2' for the first ticket",
    trigger: 'select[name*="1-simple_choice"]:last',
    run: "selectByIndex 1",
}, {
    content: "Choose the 'Q1-Answer1' answer of the 'Question1' for the second ticket",
    trigger: 'select[name*="2-simple_choice"]',
    run: "selectByIndex 1",
}, {
    content: "Choose the 'Q2-Answer2' answer of the 'Question2' for the second ticket",
    trigger: 'select[name*="2-simple_choice"]:last',
    run: "selectByIndex 2",
}, {
    content: "Choose the 'Q1-Answer2' answer of the 'Question1' for the third ticket",
    trigger: 'select[name*="3-simple_choice"]',
    run: "selectByIndex 2",
}, {
    content: "Choose the 'Q2-Answer2' answer of the 'Question2' for the third ticket",
    trigger: 'select[name*="3-simple_choice"]:last',
    run: "selectByIndex 2",
}, {
    content: "Fill the text content of the 'Question3' for the third ticket",
    trigger: 'textarea[name*="text_box"]',
    run: "edit Random answer from random guy",
}, {
    content: "Validate attendees details",
    trigger: 'button[type=submit]:last',
    run: 'click',
    expectUnloadPage: true,
},
...wsTourUtils.fillAdressForm({
    name: "Raoulette Poiluchette",
    phone: "0456112233",
    email: "raoulette@example.com",
    street: "Cheesy Crust Street, 42",
    city: "CheeseCity",
    zip: "8888",
}),
{
    content: "Confirm address",
    trigger: 'a[name="website_sale_main_button"]',
    run: "click",
    expectUnloadPage: true,
},
...wsTourUtils.payWithDemo(),
];


registry.category("web_tour.tours").add('wevent_performance_register', {
    steps: () => [].concat(
        registerSteps,
    )
});
