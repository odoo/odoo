odoo.define('website_crm.tour', function(require) {
    'use strict';

    var base = require('web_editor.base');
    var core    = require('web.core');
    var Tour    = require('web.Tour');
    var Model   = require('web.Model');
    var Session = require('web.Session');

    base.ready().done(function () {
        Tour.register({
            id:   'website_crm_tour',
            name: "Test the contact us form",
            path: '/page/contactus',
            mode: 'test',
            steps: [
                {
                    title:          "Complete name",
                    element:        "input[name=contact_name]",
                    sampleText:     "John Smith",
                },
                {
                    title:          "Complete phone number",
                    element:        "input[name=phone]",
                    sampleText:     "118.218"
                },
                {
                    title:          "Complete Email",
                    element:        "input[name=email_from]",
                    sampleText:     "john@smith.com"
                },
                {
                    title:          "Complete Company",
                    element:        "input[name=partner_name]",
                    sampleText:     "Odoo S.A."
                },
                {
                    title:          "Complete Subject",
                    element:        "input[name=name]",
                    sampleText:     "Useless message"
                },
                {
                    title:          "Complete Subject",
                    element:        "textarea[name=description]",
                    sampleText:     "Even more useless message"
                },
                {
                    title:          "Send the form",
                    element:        ".o_website_form_send"
                },
                {
                    title:          "Check we were redirected to the success page",
                    waitFor:        "#wrap:has(h1:contains('Thanks')):has(div.alert-success)"
                }
            ]
        });

        Tour.register({
            id:   'website_crm_tour_results',
            name: "Test the contact us form created records",
            path: '',
            mode: 'test',
            steps: [
                {
                    title:          "Check crm.lead record has been created",
                    waitFor:        ".o-apps",
                    onload: function (tour) {
                        var leadDef = new Model("crm.lead").call(
                            "search_read",
                            [
                                [
                                    ['contact_name', '='   , 'John Smith'],
                                    ['phone'       , '='   , '118.218'],
                                    ['email_from'  , '='   , 'john@smith.com'],
                                    ['partner_name', '='   , 'Odoo S.A.'],
                                    ['name'        , '='   , 'Useless message'],
                                    ['description' , 'like', 'Even more useless message']
                                ],
                                []
                            ]
                        );
                        var success = function(model, data) {
                            if(data.length) {
                                $('body').append('<div id="website_form_success_test_tour_'+model+'"></div>');
                            }
                        };
                        leadDef.then(_.bind(success, this, 'crm_lead'));
                    }
                },
                {
                    title:          "Check crm.lead record has been created",
                    waitFor:        "#website_form_success_test_tour_crm_lead"
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
