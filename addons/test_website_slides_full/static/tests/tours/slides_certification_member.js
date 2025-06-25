/** @odoo-module **/

import { registry } from "@web/core/registry";
import * as tourUtils from '@website_sale/js/tours/tour_utils';
import { clickOnExtraMenuItem } from "@website/js/tours/tour_utils";

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
    trigger: 'a:contains("DIY Furniture - TEST")',
    run: "click",
}, {
    content: 'eLearning: does not have access to certification',
    trigger: '.o_wslides_course_main',
    run() {
        // check that user doesn't have access to course content
        if (
            document.querySelectorAll(
                ".o_wslides_slides_list_slide .o_wslides_js_slides_list_slide_link"
            ).length === 0
        ) {
            document
                .querySelector(".o_wslides_course_main")
                .classList.add("empty-content-success");
        }
    }
}, {
    content: 'eLearning: previous step check',
    trigger: '.o_wslides_course_main.empty-content-success',
}];

var buyCertificationSteps = [{
    content: 'eLearning: try to buy course',
    trigger: 'a:contains("Add to Cart")',
    run: "click",
},
    tourUtils.goToCart(),
    tourUtils.goToCheckout(),
    ...tourUtils.payWithDemo(),
    clickOnExtraMenuItem({}),
{
    content: 'eCommerce: go back to e-learning home page',
    trigger: '.nav-item a:contains("Courses")',
    run: "click",
}, {
    content: 'eLearning: go into bought course',
    trigger: 'a:contains("DIY Furniture")',
    run: "click",
}, {
    content: 'eLearning: user should be enrolled',
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
}, {
    content: 'eLearning: start course',
    trigger: '.o_wslides_js_slides_list_slide_link',
    run: "click",
}];

var failCertificationSteps = [{
    content: 'eLearning: start certification',
    trigger: 'button:contains("Start Certification")',
    run: "click",
}, { // Question: What type of wood is the best for furniture?
    content: 'Survey: selecting answer "Fir"',
    trigger: 'div.js_question-wrapper:contains("What type of wood is the best for furniture") label:contains("Fir")',
    run: "click",
}, { // Question: Select all the furniture shown in the video
    content: 'Survey: ticking answer "Table"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Table")',
    run: "click",
}, {
    content: 'Survey: ticking answer "Bed"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Bed")',
    run: "click",
}, {
    content: 'Survey: submitting the certification with wrong answers',
    trigger: 'button:contains("Submit")',
    run: "click",
}];

var retrySteps = [{
    content: 'Survey: retry certification',
    trigger: 'a:contains("Retry")',
    run: "click",
}];

var succeedCertificationSteps = [{
    content: 'eLearning: start certification',
    trigger: 'button:contains("Start Certification")',
    run: "click",
}, { // Question: What type of wood is the best for furniture?
    content: 'Survey: selecting answer "Oak"',
    trigger: 'div.js_question-wrapper:contains("What type of wood is the best for furniture") label:contains("Oak")',
    run: "click",
}, { // Question: Select all the furniture shown in the video
    content: 'Survey: ticking answer "Chair"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Chair")',
    run: "click",
}, {
    content: 'Survey: ticking answer "Shelve"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Shelve")',
    run: "click",
}, {
    content: 'Survey: ticking answer "Desk"',
    trigger: 'div.js_question-wrapper:contains("Select all the furniture shown in the video") label:contains("Desk")',
    run: "click",
}, {
    content: 'Survey: submitting the certification with correct answers',
    trigger: 'button:contains("Submit")',
    run: "click",
}];

var certificationCompletionSteps = [{
    content: 'Survey: check certification successful',
    trigger: 'div:contains("Congratulations, you have passed the test")',
}, { // Sharing the certification
    trigger: 'a:contains("Share your certification")',
    run: "click",
}, {
    trigger: '.o_wslides_js_share_email input',
    run: "edit friend@example.com",
}, {
    trigger: '.o_wslides_js_share_email button',
    run: "click",
}, {
    trigger: '.o_wslides_js_share_email .alert:not(.d-none):contains("Sharing is caring")',
}, {
    trigger: 'button.btn-close',  // close sharing modal,
    run: "click",
}, {
    content: 'Survey: back to course home page',
    trigger: 'a:contains("Go back to course")',
    run: "click",
},
    clickOnExtraMenuItem({}),
{
    content: 'eLearning: back to e-learning home page',
    trigger: '.nav-item a:contains("Courses")',
    run: "click",
}, {
    content: 'eLearning: course should be completed',
    trigger: '.o_wslides_course_card:contains("DIY Furniture") .badge:contains("Completed")',
}];

var profileSteps = [{
    content: 'eLearning: access user profile',
    trigger: '.o_wslides_home_aside_loggedin a:contains("View")',
    run: "click",
}, {
    content: 'eLearning: check that the user profile certifications include the new certification',
    trigger: '.o_wprofile_slides_course_card_body:contains("Furniture Creation Certification")',
}];

registry.category("web_tour.tours").add('certification_member', {
    url: '/slides',
    steps: () => [].concat(
        initTourSteps,
        buyCertificationSteps,
        failCertificationSteps,
        retrySteps,
        failCertificationSteps,
        retrySteps,
        failCertificationSteps,
        [{
            trigger: 'a:contains("Go back to course")',
            run: "click",
        }],
        buyCertificationSteps,
        succeedCertificationSteps,
        certificationCompletionSteps,
        profileSteps
    )
});
