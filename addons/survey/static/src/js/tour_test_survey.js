odoo.define('survey.tour_test_survey', function (require) {
'use strict';

var tour = require('web_tour.tour');
var base = require("web_editor.base");

tour.register('test_survey', {
    test: true,
    url: '/survey/start/user-feedback-form-1/phantom',
    wait_for: base.ready()
},
    [
        // Page-1
        {
            content: "Clicking on Start Survey",
            trigger: 'a.btn.btn-primary.btn-lg:contains("Start Survey")',
        },
        // Question: Where do you develop your new features?
        {
            content: "Selecting answer 'Yes, I use a version < 7.0'",
            trigger: 'select[name="1_1_1"]',
            run: 'text 1',
        },
        // Question: Which modules are you using/testing?
        {
            content: "Ticking answer 'Sales Management'",
            trigger: 'input[name="1_1_2_5"][value="5"]',
            run: 'text 5',
        },
        {
            content: "Clicking on Next Page",
            trigger: 'button[value="next"]',
        },
        // Page-2
        // Question: What do you think about the documentation available on doc.odoo.com?
        {
            content: "For 'It is up-to-date' checking 'Totally disagree'",
            trigger: 'input[name="1_2_3_15"][value="11"]',
            run: 'text 11',
        },
        {
            content: "For 'It helps in the beginning' ckecking 'Disagree'",
            trigger: 'input[name="1_2_3_16"][value="12"]',
            run: 'text 12',
        },
        {
            content: "For 'I use the contextual help in Odoo' checking 'Agree'",
            trigger: 'input[name="1_2_3_17"][value="13"]',
            run: 'text 13',
        },
        {
            content: "For 'It is complete' checking 'Totally disagree'",
            trigger: 'input[name="1_2_3_18"][value="11"]',
            run: 'text 11',
        },
        {
            content: "For 'It is clear' checking 'Disagree'",
            trigger: 'input[name="1_2_3_19"][value="12"]',
            run: 'text 12',
        },
        // Question: What do you think about the process views of Odoo, available in the web client ?
        {
            content: "For 'They help new users to understand Odoo' checking 'Totally disagree'",
            trigger: 'input[name="1_2_4_24"][value="20"]',
            run: 'text 20',
        },
        {
            content: "For 'They are clean and correct' checking 'Totally disagree'",
            trigger: 'input[name="1_2_4_25"][value="20"]',
            run: 'text 20',
        },
        {
            content: "For 'They are useful on a daily usage' checking 'Totally disagree'",
            trigger: 'input[name="1_2_4_26"][value="20"]',
            run: 'text 20',
        },
        {
            content: "For 'A process is defined for all enterprise flows' checking 'Disagree'",
            trigger: 'input[name="1_2_4_27"][value="21"]',
            run: 'text 21',
        },
        {
            content: "For 'It's easy to find the process you need' checking 'Agree'",
            trigger: 'input[name="1_2_4_28"][value="22"]',
            run: 'text 22',
        },
        // Question: Do you have suggestions on how to improve the process view?
        {
            content: "Writing answer",
            trigger: 'textarea[name="1_2_5"]',
            run: 'text I do not want to provide any suggestions.',
        },
        // Question: What do you think about the structure of the menus?
        {
            content: "Checking 'It can be improved'",
            trigger: 'input[name="1_2_6_30"][value="30"]',
            run: 'text 30',
        },
        // Question: What do you think about the groups of users?
        {
            content: "For 'The security rules defined on groups are useful' checking 'Agree'",
            trigger: 'input[name="1_2_7_36"][value="32"]',
            run: 'text 32',
        },
        {
            content: "For 'Those security rules are standard and can be used out-of-the-box in most cases' checking 'Totally agree'",
            trigger: 'input[name="1_2_7_37"][value="35"]',
            run: 'text 35',
        },
        {
            content: "For 'The 'Usability/Extended View' group helps in daily work' checking 'Totally agree'",
            trigger: 'input[name="1_2_7_38"][value="35"]',
            run: 'text 35',
        },
        {
            content: "For 'The 'Usability/Extended View' group hides only optional fields' checking 'Totally agree'",
            trigger: 'input[name="1_2_7_39"][value="33"]',
            run: 'text 33',
        },
        {
            content: "For 'The groups set on menu items are relevant' checking 'Totally disagree'",
            trigger: 'input[name="1_2_7_40"][value="32"]',
            run: 'text 32',
        },
        // Question: What do you think about the structure of the menus?
        {
            content: "Checking 'There are too few groups defined, security isn't accurate enough'",
            trigger: 'input[name="1_2_8"][value="42"]',
            run: 'text 42',
        },
        // Question: What do you think about configuration wizards?
        {
            content: "For 'Descriptions and help tooltips are clear enough' checking 'Agree'",
            trigger: 'input[name="1_2_9_48"][value="46"]',
            run: 'text 46',
        },
        {
            content: "For 'Configuration wizard exists for each important setting' checking 'Agree'",
            trigger: 'input[name="1_2_9_49"][value="46"]',
            run: 'text 46',
        },
        {
            content: "For 'Extra modules proposed are relevant' checking 'Totally agree'",
            trigger: 'input[name="1_2_9_50"][value="47"]',
            run: 'text 47',
        },
        {
            content: "For 'Running the configuration wizards is a good way to spare time' checking 'Totally disagree'",
            trigger: 'input[name="1_2_9_51"][value="44"]',
            run: 'text 44',
        },
        {
            content: "Clicking on Next Page",
            trigger: 'button[value="next"]',
        },
        // Page-3
        // Question: How do you contribute or plan to contribute to Odoo?
        {
            content: "Checking 'I would like to contribute but I don not know how?'",
            trigger: 'input[name="1_3_10_53"][value="53"]',
            run: 'text 53',
        },
        // Question: Do you have a proposition to help people to contribute?
        {
            content: "Writing answer",
            trigger: 'textarea[name="1_3_11"]',
            run: 'text No. I do not have any proposition to help people to contribute.',
        },
        // Question: Do you have a proposition to attract new contributors?
        {
            content: "Writing answer",
            trigger: 'textarea[name="1_3_12"]',
            run: 'text No. I do not have any proposition to Attract new contributors.',
        },
        {
            content: "Clicking on Next Page",
            trigger: 'button[value="next"]',
        },
        // Page-4
        // Question: Where do you develop your new features?
        {
            content: "Checking 'I host them on my own website'",
            trigger: 'input[name="1_4_13_59"][value="59"]',
            run: 'text 59',
        },
        {
            content: "Finish Survey",
            trigger: 'button[value="finish"]',
        },
        {
            content: "Thank you",
            trigger: 'h1:contains("Thank you!")',
        }
    ]
);

});
