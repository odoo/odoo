odoo.define('test_certification_flow.certification_flow_tour', function (require) {
"use strict";

var tour = require('web_tour.tour');

/**
 * The purpose of this tour is to check the whole certification flow:
 *
 * -> student (= demo user) checks 'on payment' course content
 * -> clicks on "buy course"
 * -> is redirected to webshop on the product page
 * -> buys the course
 * -> fails 3 times, exhausting his attempts
 * -> is removed to the members of the course
 * -> buys the course again
 * -> succeeds the certification
 * -> has the course marked as completed
 * -> has the certification in his user profile
 *
 */

var initTourSteps = [{
    content: "Check certification course content",
    trigger: 'a:contains("DIY Furniture")'
}, {
    content: "The student does not have access to the content",
    trigger: '.o_wslides_course_main',
    run: function () {
        // check that user doesn't have access to course content
        if ($('.o_wslides_slides_list_slide .o_wslides_js_slides_list_slide_link').length === 0) {
            $('.o_wslides_course_main').addClass('empty-content-success');
        }
    }
}, {
    trigger: '.o_wslides_course_main.empty-content-success',
    run: function () {} // check that previous step succeeded
}];

var buyCertificationSteps = [{
    content: "Buy the course",
    trigger: 'a:contains("Buy Course")'
}, {
    content: "Select the 'test' payment acquirer",
    trigger: '.o_payment_acquirer_select:contains("Test")'
}, {
    content: "Input card number",
    trigger: 'input[name="cc_number"]',
    run: 'text 4242424242424242'
}, {
    content: "Input card's holder name",
    trigger: 'input[name="cc_holder_name"]',
    run: 'text Marc Demo'
}, {
    content: "Input card expiry date",
    trigger: 'input[name="cc_expiry"]',
    run: 'text 11 / 50'
}, {
    content: "Input card cvc",
    trigger: 'input[name="cvc"]',
    run: 'text 999'
}, {
    content: "Trigger the payment",
    trigger: '#o_payment_form_pay'
}, {
    content: "Check that the payment is successful",
    trigger: '.oe_website_sale_tx_status:contains("Your online payment has been successfully processed")',
    run: function () {}
}, {
    content: "Go back to e-learning home page",
    trigger: '.nav-link:contains("Courses")'
}, {
    content: "Select the right course",
    trigger: 'a:contains("DIY Furniture")'
}, {
    content: "Check that the user is correctly enrolled",
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {}
}, {
    content: "Start the course",
    trigger: '.o_wslides_js_slides_list_slide_link'
}];

var failCertificationSteps = [{
    content: "Start the certification",
    trigger: 'a:contains("Start Certification")'
}, { // Question: What type of wood is the best for furniture?
    content: "Selecting answer 'Fir'",
    trigger: 'div.js_question-wrapper:contains("What type of wood is the best for furniture") select',
    run: 'text Fir',
}, { // Question: Select all the furniture shown in the video
    content: "Ticking answer 'Table'",
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Table") input'
}, {
    content: "Ticking answer 'Bed'",
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Bed") input'
}, {
    content: "Submitting the certification with wrong answers",
    trigger: 'button:contains("Submit survey")'
}];

var retrySteps = [{
    content: "Retry the certification",
    trigger: 'a:contains("Retry")'
}];

var succeedCertificationSteps = [{
    content: "Start the certification",
    trigger: 'a:contains("Start Certification")'
}, { // Question: What type of wood is the best for furniture?
    content: "Selecting answer 'Oak'",
    trigger: 'div.js_question-wrapper:contains("What type of wood is the best for furniture") select',
    run: 'text Oak',
}, { // Question: Select all the furniture shown in the video
    content: "Ticking answer 'Chair'",
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Chair") input'
}, {
    content: "Ticking answer 'Shelve'",
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Shelve") input'
}, {
    content: "Ticking answer 'Desk'",
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Desk") input'
}, {
    content: "Submitting the certification with correct answers",
    trigger: 'button:contains("Submit survey")'
}];

var certificationCompletionSteps = [{
    content: "Check certification successful",
    trigger: 'div:contains("Congratulations, you have passed the test")',
    run: function () {}
}, {
    content: "Go back to course home page",
    trigger: 'a:contains("Go back to course")'
}, {
    content: "Go back to e-learning home page",
    trigger: '.nav-link:contains("Courses")'
}, {
    content: "Check course marked as completed",
    trigger: '.o_wslides_course_card:contains("DIY Furniture") .badge-pill:contains("Completed")',
    run: function () {}
}];

var profileSteps = [{
    content: "Access user profile",
    trigger: '.o_wslides_home_aside_loggedin a:contains("View")'
}, {
    content: "Check that the user profile certifications include the new certification",
    trigger: '.o_wprofile_slides_course_card_body:contains("Furniture Creation Certification")',
    run: function () {}
}];

tour.register('certification_flow_tour', {
    url: '/slides',
    test: true
}, [].concat(
        initTourSteps,
        buyCertificationSteps,
        failCertificationSteps,
        retrySteps,
        failCertificationSteps,
        retrySteps,
        failCertificationSteps,
        [{trigger: 'a:contains("Go back to course")'}],
        buyCertificationSteps,
        succeedCertificationSteps,
        certificationCompletionSteps,
        profileSteps
    )
);

});
