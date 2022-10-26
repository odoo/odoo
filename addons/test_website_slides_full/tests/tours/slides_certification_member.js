odoo.define('test_website_slides_full.tour.slide.certification.member', function (require) {
"use strict";

var tour = require('web_tour.tour');
const tourUtils = require('website_sale.tour_utils');

/**
 * The purpose of this tour is to check the whole certification flow:
 *
 * -> student (= demo user) checks 'on payment' course content
 * -> clicks on "buy course"
 * -> is redirected to webshop on the product page
 * -> buys the course
 * -> fails 3 times, exhausting their attempts
 * -> is removed to the members of the course
 * -> buys the course again
 * -> succeeds the certification
 * -> has the course marked as completed
 * -> has the certification in their user profile
 *
 */

var initTourSteps = [{
    content: 'eLearning: go to certification course',
    trigger: 'a:contains("DIY Furniture - TEST")'
}, {
    content: 'eLearning: does not have access to certification',
    trigger: '.o_wslides_course_main',
    run: function () {
        // check that user doesn't have access to course content
        if ($('.o_wslides_slides_list_slide .o_wslides_js_slides_list_slide_link').length === 0) {
            $('.o_wslides_course_main').addClass('empty-content-success');
        }
    }
}, {
    content: 'eLearning: previous step check',
    trigger: '.o_wslides_course_main.empty-content-success',
    run: function () {} // check that previous step succeeded
}];

var buyCertificationSteps = [{
    content: 'eLearning: try to buy course',
    trigger: 'a:contains("Add to Cart")'
},
    tourUtils.goToCart(),
{
    content: 'eCommerce: Process Checkout',
    trigger: 'a:contains("Process Checkout")'
}, {
    content: 'eCommerce: select Test payment provider',
    trigger: '.o_payment_option_card:contains("Demo")'
}, {
    content: 'eCommerce: add card number',
    trigger: 'input[name="customer_input"]',
    run: 'text 4242424242424242'
}, {
    content: 'eCommerce: pay',
    trigger: 'button[name="o_payment_submit_button"]'
}, {
    content: 'eCommerce: check that the payment is successful',
    trigger: '.oe_website_sale_tx_status:contains("Your payment has been successfully processed.")',
    run: function () {}
}, {
    content: 'eCommerce: go back to e-learning home page',
    trigger: '.nav-link:contains("Courses")'
}, {
    content: 'eLearning: go into bought course',
    trigger: 'a:contains("DIY Furniture")'
}, {
    content: 'eLearning: user should be enrolled',
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
    run: function () {}
}, {
    content: 'eLearning: start course',
    trigger: '.o_wslides_js_slides_list_slide_link'
}];

var failCertificationSteps = [{
    content: 'eLearning: start certification',
    trigger: 'button:contains("Start Certification")'
}, { // Question: What type of wood is the best for furniture?
    content: 'Survey: selecting answer "Fir"',
    trigger: 'div.js_question-wrapper:contains("What type of wood is the best for furniture") label:contains("Fir")'
}, { // Question: Select all the furniture shown in the video
    content: 'Survey: ticking answer "Table"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Table")'
}, {
    content: 'Survey: ticking answer "Bed"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Bed")'
}, {
    content: 'Survey: submitting the certification with wrong answers',
    trigger: 'button:contains("Submit")'
}];

var retrySteps = [{
    content: 'Survey: retry certification',
    trigger: 'a:contains("Retry")'
}];

var succeedCertificationSteps = [{
    content: 'eLearning: start certification',
    trigger: 'button:contains("Start Certification")'
}, { // Question: What type of wood is the best for furniture?
    content: 'Survey: selecting answer "Oak"',
    trigger: 'div.js_question-wrapper:contains("What type of wood is the best for furniture") label:contains("Oak")',
}, { // Question: Select all the furniture shown in the video
    content: 'Survey: ticking answer "Chair"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Chair")'
}, {
    content: 'Survey: ticking answer "Shelve"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Shelve")'
}, {
    content: 'Survey: ticking answer "Desk"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Desk")'
}, {
    content: 'Survey: submitting the certification with correct answers',
    trigger: 'button:contains("Submit")'
}];

var certificationCompletionSteps = [{
    content: 'Survey: check certification successful',
    trigger: 'div:contains("Congratulations, you have passed the test")',
    run: function () {}
}, {
    content: 'Survey: back to course home page',
    trigger: 'a:contains("Go back to course")'
}, {
    content: 'eLearning: back to e-learning home page',
    trigger: '.nav-link:contains("Courses")'
}, {
    content: 'eLearning: course should be completed',
    trigger: '.o_wslides_course_card:contains("DIY Furniture") .rounded-pill:contains("Completed")',
    run: function () {}
}];

var profileSteps = [{
    content: 'eLearning: access user profile',
    trigger: '.o_wslides_home_aside_loggedin a:contains("View")'
}, {
    content: 'eLearning: check that the user profile certifications include the new certification',
    trigger: '.o_wprofile_slides_course_card_body:contains("Furniture Creation Certification")',
    run: function () {}
}];

tour.register('certification_member', {
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
