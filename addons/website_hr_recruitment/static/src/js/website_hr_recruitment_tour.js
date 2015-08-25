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
                    sampleText:     "A completely useless message"
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

        Tour.register({
            id:   'website_hr_recruitment_tour_results',
            name: "Check the hr applicants form created records",
            path: '',
            mode: 'test',
            steps: [
                {
                    title:          "Check hr.applicant record has been created",
                    waitFor:        ".o-apps",
                    onload: function (tour) {
                        var hrDef = new Model("hr.applicant").call(
                            "search_read",
                            [
                                [
                                    ['partner_name'    , '='   , 'John Smith'],
                                    ['partner_phone'   , '='   , '118.218'],
                                    ['email_from'      , '='   , 'john@smith.com'],
                                    ['description'     , 'like', 'A completely useless message']
                                ],
                                []
                            ]
                        );
                        var success = function(model, data) {
                            if(data.length) {
                                $('body').append('<div id="website_form_success_test_tour_'+model+'"></div>');
                            }
                        };
                        hrDef.then(_.bind(success, this, 'hr_applicant'));
                    }
                },
                {
                    title:          "Check hr.applicant record has been created",
                    waitFor:        "#website_form_success_test_tour_hr_applicant"
                },
                {
                    title:          "Final Step",
                    waitFor:        "html"
                }
            ]
        });
    });

    return {};
});
