import { registry } from "@web/core/registry";

/**
 * This tour validates the complete certification flow for a student (= portal user).
 *
 * The tour consists of two main scenarios:
 *
 * 1. **Failure Attempts**
 *    - The student is redirected to the "All Courses" page.
 *    - Navigates to the certification course.
 *    - Starts the certification process.
 *    - Fails the test 3 times, exhausting all attempts.
 *    - Is removed from the course members.
 *
 * 2. **Successful Attempt**
 *    - The student is redirected to the "All Courses" page.
 *    - Navigates to the certification course.
 *    - Starts the certification process.
 *    - Successfully completes the certification.
 *    - The course is marked as completed.
 *    - The certification is added to their user profile.
 */

var startCertificationSurvey = [{
    content: 'eLearning: go to certification course',
    trigger: 'a:contains("DIY Furniture - TEST")',
    run: "click",
    expectUnloadPage: true,
}, {
    content: 'eLearning: user should be enrolled',
    trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
}, {
    content: 'eLearning: start course',
    trigger: '.o_wslides_js_slides_list_slide_link',
    run: "click",
    expectUnloadPage: true,
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
}, {
    content: "Click on Submit",
    trigger: 'button.btn-primary:contains("Submit")',
    run: "click",
}];

var retrySteps = [{
    content: 'Survey: retry certification',
    trigger: 'a:contains("Retry")',
    run: "click",
    expectUnloadPage: true,
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
}, {
    content: "Click on Submit",
    trigger: 'button.btn-primary:contains("Submit")',
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
    expectUnloadPage: true,
}, {
    content: 'eLearning: course should be completed',
    trigger: '.o_wslides_channel_completion_completed',
}];

var profileSteps = [{
    content: 'eLearning: back to e-learning home page',
    trigger: 'a:contains("Courses")',
    run: "click",
    expectUnloadPage: true,
}, {
    content: 'eLearning: access user profile',
    trigger: '.o_wslides_home_aside_loggedin a:contains("View")',
    run: "click",
    expectUnloadPage: true,
}, {
    content: 'eLearning: check that the user profile certifications include the new certification',
    trigger: '.o_wprofile_slides_course_card_body:contains("Furniture Creation Certification")',
}];

registry.category("web_tour.tours").add('certification_member_failure', {
    url: '/slides',
    steps: () => [].concat(
        startCertificationSurvey,
        failCertificationSteps,
        retrySteps,
        failCertificationSteps,
        retrySteps,
        failCertificationSteps
    )
});

registry.category("web_tour.tours").add('certification_member_success', {
    url: '/slides',
    steps: () => [].concat(
        startCertificationSurvey,
        succeedCertificationSteps,
        certificationCompletionSteps,
        profileSteps
    )
});
