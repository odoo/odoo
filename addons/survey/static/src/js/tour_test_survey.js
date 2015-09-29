odoo.define('survey.tour_test_survey', function (require) {
'use strict';
var Core = require('web.core');
var Tour = require('web.Tour');
var _t = Core._t;


Tour.register({
    id:   'test_survey',
    name: _t("try to create and fill survey"),
    path: '/survey/start/user-feedback-form-1/phantom',
    mode: 'test',
    steps: [
        // Page-1
        {
            title:     "Clicking on Start Survey",
            element:   'a.btn.btn-primary.btn-lg:contains("Start Survey")',
        },
        // Question: Where do you develop your new features?
        {
            title:     "Selecting answer 'Yes, I use a version < 7.0'",
            element:   'select[name="1_1_1"]',
            sampleText:'1',
        },
        // Question: Which modules are you using/testing?
        {
            title:     "Ticking answer 'Sales Management'",
            element:   'input[name="1_1_2_5"][value="5"]',
            sampleText:'5',
        },
        {
            title:     "Clicking on Next Page",
            element:   'button[value="next"]',
        },
        // Page-2
        // Question: What do you think about the documentation available on doc.odoo.com?
        {
            title:     "For 'It is up-to-date' checking 'Totally disagree'",
            element:   'input[name="1_2_3_15"][value="11"]',
            sampleText:'11',
        },
        {
            title:     "For 'It helps in the beginning' ckecking 'Disagree'",
            element:   'input[name="1_2_3_16"][value="12"]',
            sampleText:'12',
        },
        {
            title:     "For 'I use the contextual help in Odoo' checking 'Agree'",
            element:   'input[name="1_2_3_17"][value="13"]',
            sampleText:'13',
        },
        {
            title:     "For 'It is complete' checking 'Totally disagree'",
            element:   'input[name="1_2_3_18"][value="11"]',
            sampleText:'11',
        },
        {
            title:     "For 'It is clear' checking 'Disagree'",
            element:   'input[name="1_2_3_19"][value="12"]',
            sampleText:'12',
        },
        // Question: What do you think about the process views of Odoo, available in the web client ?
        {
            title:     "For 'They help new users to understand Odoo' checking 'Totally disagree'",
            element:   'input[name="1_2_4_24"][value="20"]',
            sampleText:'20',
        },
        {
            title:     "For 'They are clean and correct' checking 'Totally disagree'",
            element:   'input[name="1_2_4_25"][value="20"]',
            sampleText:'20',
        },
        {
            title:     "For 'They are useful on a daily usage' checking 'Totally disagree'",
            element:   'input[name="1_2_4_26"][value="20"]',
            sampleText:'20',
        },
        {
            title:     "For 'A process is defined for all enterprise flows' checking 'Disagree'",
            element:   'input[name="1_2_4_27"][value="21"]',
            sampleText:'21',
        },
        {
            title:     "For 'It's easy to find the process you need' checking 'Agree'",
            element:   'input[name="1_2_4_28"][value="22"]',
            sampleText:'22',
        },
        // Question: Do you have suggestions on how to improve the process view?
        {
            title:     "Writing answer",
            element:   'textarea[name="1_2_5"]',
            sampleText:'I do not want to provide any suggestions.',
        },
        // Question: What do you think about the structure of the menus?
        {
            title:     "Checking 'It can be improved'",
            element:   'input[name="1_2_6_30"][value="30"]',
            sampleText:'30',
        },
        // Question: What do you think about the groups of users?
        {
            title:     "For 'The security rules defined on groups are useful' checking 'Agree'",
            element:   'input[name="1_2_7_36"][value="32"]',
            sampleText:'32',
        },
        {
            title:     "For 'Those security rules are standard and can be used out-of-the-box in most cases' checking 'Totally agree'",
            element:   'input[name="1_2_7_37"][value="35"]',
            sampleText:'35',
        },
        {
            title:     "For 'The 'Usability/Extended View' group helps in daily work' checking 'Totally agree'",
            element:   'input[name="1_2_7_38"][value="35"]',
            sampleText:'35',
        },
        {
            title:     "For 'The 'Usability/Extended View' group hides only optional fields' checking 'Totally agree'",
            element:   'input[name="1_2_7_39"][value="33"]',
            sampleText:'33',
        },
        {
            title:     "For 'The groups set on menu items are relevant' checking 'Totally disagree'",
            element:   'input[name="1_2_7_40"][value="32"]',
            sampleText:'32',
        },
        // Question: What do you think about the structure of the menus?
        {
            title:     "Checking 'There are too few groups defined, security isn't accurate enough'",
            element:   'input[name="1_2_8"][value="42"]',
            sampleText:'42',
        },
        // Question: What do you think about configuration wizards?
        {
            title:     "For 'Descriptions and help tooltips are clear enough' checking 'Agree'",
            element:   'input[name="1_2_9_48"][value="46"]',
            sampleText:'46',
        },
        {
            title:     "For 'Configuration wizard exists for each important setting' checking 'Agree'",
            element:   'input[name="1_2_9_49"][value="46"]',
            sampleText:'46',
        },
        {
            title:     "For 'Extra modules proposed are relevant' checking 'Totally agree'",
            element:   'input[name="1_2_9_50"][value="47"]',
            sampleText:'47',
        },
        {
            title:     "For 'Running the configuration wizards is a good way to spare time' checking 'Totally disagree'",
            element:   'input[name="1_2_9_51"][value="44"]',
            sampleText:'44',
        },
        {
            title:     "Clicking on Next Page",
            element:   'button[value="next"]',
        },
        // Page-3
        // Question: How do you contribute or plan to contribute to Odoo?
        {
            title:     "Checking 'I would like to contribute but I don not know how?'",
            element:   'input[name="1_3_10_53"][value="53"]',
            sampleText:'53',
        },
        // Question: Do you have a proposition to help people to contribute?
        {
            title:     "Writing answer",
            element:   'textarea[name="1_3_11"]',
            sampleText:'No. I do not have any proposition to help people to contribute.',
        },
        // Question: Do you have a proposition to attract new contributors?
        {
            title:     "Writing answer",
            element:   'textarea[name="1_3_12"]',
            sampleText:'No. I do not have any proposition to Attract new contributors.',
        },
        {
            title:     "Clicking on Next Page",
            element:   'button[value="next"]',
        },
        // Page-4
        // Question: Where do you develop your new features?
        {
            title:     "Checking 'I host them on my own website'",
            element:   'input[name="1_4_13_59"][value="59"]',
            sampleText:'59',
        },
        {
            title:     "Finish Survey",
            element:   'button[value="finish"]',
        },
        {
            title:     "Thank you",
            element:   'h1:contains("Thank you!")',
        }
    ]
});

});
