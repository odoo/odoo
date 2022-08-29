odoo.define('test_event_full.tour.performance', function (require) {
"use strict";

var tour = require('web_tour.tour');

var registerSteps = [{
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
    trigger: 'form[id="attendee_registration"] .btn:contains("Continue")',
    run: function () {
        $("input[name='1-name']").val("Raoulette Poiluchette");
        $("input[name='1-phone']").val("0456112233");
        $("input[name='1-email']").val("raoulette@example.com");
        $("div[name*='Question1'] select[name*='question_answer-1']").val($("select[name*='question_answer-1'] option:contains('Q1-Answer2')").val());
        $("div[name*='Question2'] select[name*='question_answer-1']").val($("select[name*='question_answer-1'] option:contains('Q2-Answer1')").val());
        $("input[name='2-name']").val("Michel Tractopelle");
        $("input[name='2-phone']").val("0456332211");
        $("input[name='2-email']").val("michel@example.com");
        $("div[name*='Question1'] select[name*='question_answer-2']").val($("select[name*='question_answer-2'] option:contains('Q1-Answer1')").val());
        $("div[name*='Question2'] select[name*='question_answer-2']").val($("select[name*='question_answer-2'] option:contains('Q2-Answer2')").val());
        $("input[name='3-name']").val("Hubert Boitaclous");
        $("input[name='3-phone']").val("0456995511");
        $("input[name='3-email']").val("hubert@example.com");
        $("div[name*='Question1'] select[name*='question_answer-3']").val($("select[name*='question_answer-3'] option:contains('Q1-Answer2')").val());
        $("div[name*='Question2'] select[name*='question_answer-3']").val($("select[name*='question_answer-3'] option:contains('Q2-Answer2')").val());
        $("textarea[name*='question_answer']").text("Random answer from random guy");
    },
}, {
    content: "Validate attendees details",
    extra_trigger: "input[name='1-name'], input[name='2-name'], input[name='3-name']",
    trigger: 'button:contains("Continue")',
    run: 'click',
}, {
    content: "Address filling",
    trigger: 'select[name="country_id"]',
    run: function () {
        $('input[name="name"]').val('Raoulette Poiluchette');
        $('input[name="phone"]').val('0456112233');
        $('input[name="email"]').val('raoulette@example.com');
        $('input[name="street"]').val('Cheesy Crust Street, 42');
        $('input[name="city"]').val('CheeseCity');
        $('input[name="zip"]').val('8888');
        $('#country_id option:eq(1)').attr('selected', true);
    },
}, {
    content: "Next",
    trigger: '.oe_cart .btn:contains("Next")',
}, {
    content: 'Select Test payment acquirer',
    trigger: '.o_payment_option_card:contains("Demo")'
}, {
    content: 'Add card number',
    trigger: 'input[name="customer_input"]',
    run: 'text 4242424242424242'
}, {
    content: "Pay now",
    extra_trigger: "#cart_products:contains(Ticket1):contains(Ticket2)",
    trigger: 'button:contains(Pay Now)',
    run: 'click',
}, {
    content: 'Payment is successful',
    trigger: '.oe_website_sale_tx_status:contains("Your payment has been successfully processed.")',
    run: function () {}
}];


tour.register('wevent_performance_register', {
    test: true
}, [].concat(
        registerSteps,
    )
);

});
