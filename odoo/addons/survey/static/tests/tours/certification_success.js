/** @odoo-module **/

/**
 * Speed up fade-in fade-out to avoid useless delay in tests.
 */
function patchSurveyWidget() {
    const SurveyFormWidget = odoo.loader.modules.get('@survey/js/survey_form')[Symbol.for('default')]
    SurveyFormWidget.include({
        _submitForm: function () {
            this.fadeInOutDelay = 0;
            return this._super.apply(this, arguments);
        }
    });
}

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('test_certification_success', {
    test: true,
    url: '/survey/start/4ead4bc8-b8f2-4760-a682-1fde8daaaaac',
    steps: () => [{
        content: "Patching Survey Widget",
        trigger: 'body',
        run: function(){
            patchSurveyWidget();
        }
    }, { // Page-1
        content: "Clicking on Start Certification",
        trigger: 'button.btn.btn-primary.btn-lg:contains("Start Certification")',
    }, { // Question: Do we sell Acoustic Bloc Screens?
        content: "Selecting answer 'Yes'",
        trigger: 'div.js_question-wrapper:contains("Do we sell Acoustic Bloc Screens") label:contains("Yes")',
    }, { // Question: Select all the existing products
        content: "Ticking answer 'Chair floor protection'",
        trigger: 'div.js_question-wrapper:contains("Select all the existing products") label:contains("Chair floor protection")'
    }, {
        content: "Ticking answer 'Drawer'",
        trigger: 'div.js_question-wrapper:contains("Select all the existing products") label:contains("Drawer")'
    }, {
        content: "Ticking answer 'Conference chair'",
        trigger: 'div.js_question-wrapper:contains("Select all the existing products") label:contains("Conference chair")'
    }, { // Question: Select all the available customizations for our Customizable Desk
        content: "Ticking answer 'Color'",
        trigger: 'div.js_question-wrapper:contains("Select all the available customizations for our Customizable Desk") label:contains("Color")'
    }, {
        content: "Ticking answer 'Legs'",
        trigger: 'div.js_question-wrapper:contains("Select all the available customizations for our Customizable Desk") label:contains("Legs")'
    }, { // Question: How many versions of the Corner Desk do we have?
        content: "Selecting answer '2'",
        trigger: 'div.js_question-wrapper:contains("How many versions of the Corner Desk do we have") label:contains("2")',
    }, { // Question: Do you think we have missing products in our catalog? (not rated)
        content: "Missing products",
        trigger: 'div.js_question-wrapper:contains("Do you think we have missing products in our catalog") textarea',
        run: "text I think we should make more versions of the customizable desk, it's such an amazing product!",
    }, { // Page-2 Question: How much do we sell our Cable Management Box?
        content: "Selecting answer '$80' (wrong one)",
        trigger: 'div.js_question-wrapper:contains("How much do we sell our Cable Management Box") label:contains("$80")',
    }, { // Question: Select all the products that sell for $100 or more
        content: "Ticking answer 'Corner Desk Right Sit'",
        trigger: 'div.js_question-wrapper:contains("Select all the products that sell for $100 or more") label:contains("Corner Desk Right Sit")'
    }, {
        content: "Ticking answer 'Desk Combination'",
        trigger: 'div.js_question-wrapper:contains("Select all the products that sell for $100 or more") label:contains("Desk Combination")'
    }, {
        content: "Ticking answer 'Large Desk'",
        trigger: 'div.js_question-wrapper:contains("Select all the products that sell for $100 or more") label:contains("Large Desk")'
    }, { // Question: What do you think about our prices (not rated)?
        content: "Selecting answer 'Underpriced'",
        trigger: 'div.js_question-wrapper:contains("What do you think about our prices") label:contains("Underpriced")',
    }, { // Page-3 Question: How many days is our money-back guarantee?
        content: "Inputting answer '30'",
        trigger: 'div.js_question-wrapper:contains("How many days is our money-back guarantee") input',
        run: 'text 30'
    }, { // Question: If a customer purchases a product on 6 January 2020, what is the latest day we expect to ship it?
        content: "Inputting answer '01/08/2020'",
        trigger: 'div.js_question-wrapper:contains("If a customer purchases a product on 6 January 2020, what is the latest day we expect to ship it") input',
        run: 'text 01/08/2020'
    }, { // Question: If a customer purchases a 1 year warranty on 6 January 2020, when do we expect the warranty to expire?
        content: "Inputting answer '01/07/2021 00:00:01'",
        trigger: 'div.js_question-wrapper:contains("If a customer purchases a 1 year warranty on 6 January 2020, when do we expect the warranty to expire") input',
        run: 'text 01/07/2021 00:00:01'
    }, { // Question: What day to you think is best for us to start having an annual sale (not rated)?
        content: "Inputting answer '01/01/2021'",
        trigger: 'div.js_question-wrapper:contains("What day to you think is best for us to start having an annual sale (not rated)") input',
        run: 'text 01/01/2021'
    }, { // Question: What day and time do you think most customers are most likely to call customer service (not rated)?
        content: "Inputting answer '01/01/2021 13:00:01'",
        trigger: 'div.js_question-wrapper:contains("What day and time do you think most customers are most likely to call customer service (not rated)") input',
        run: 'text 01/01/2021 13:00:01'
    }, { // Question: How many chairs do you think we should aim to sell in a year (not rated)?
        content: "Inputting answer '1000'",
        trigger: 'div.js_question-wrapper:contains("How many chairs do you think we should aim to sell in a year (not rated)") input',
        run: 'text 1000'
    }, {
        content: "Finish Survey",
        trigger: 'button[type="submit"]',
    }, {
        content: "Thank you",
        trigger: 'h1:contains("Thank you!")',
    }, {
        content: "test passed",
        trigger: 'div:contains("Congratulations, you have passed the test!")',
        isCheck: true,
    }
]});
