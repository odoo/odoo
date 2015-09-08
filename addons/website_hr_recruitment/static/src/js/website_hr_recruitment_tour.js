odoo.define('website_hr_recruitment.tour', function(require) {
    'use strict';

    var base = require('web_editor.base');
    var core    = require('web.core');
    var Tour    = require('web.Tour');
    var Model   = require('web.Model');
    var Session = require('web.Session');

    base.ready().done(function () {
        Tour.register({
            id:   'website_hr_recruitment_tour',
            name: "Test the hr applicants form",
            path: '/jobs/apply/3',
            mode: 'test',
            steps: [
                {
                    title:          "Complete name",
                    element:        "input[name=partner_name]",
                    sampleText:     "John Smith"
                },
                {
                    title:          "Complete Email",
                    element:        "input[name=email_from]",
                    sampleText:     "john@smith.com"
                },
                {
                    title:          "Complete phone number",
                    element:        "input[name=partner_phone]",
                    sampleText:     "118.218"
                },
                {
                    title:          "Complete Subject",
                    element:        "textarea[name=description]",
                    sampleText:     "### HR RECRUITMENT TEST DATA ###"
                },
                // TODO: Upload a file ?
                {
                    title:          "Send the form",
                    element:        ".o_website_form_send"
                },
                {
                    title:          "Check the form is submited without errors",
                    waitFor:        ".oe_structure:has(h1:contains('Thank you!'))"
                }
            ]
        });
    });

    return {};
});
