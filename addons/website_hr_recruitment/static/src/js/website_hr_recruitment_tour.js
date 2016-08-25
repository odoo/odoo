odoo.define('website_hr_recruitment.tour', function(require) {
    'use strict';

    var base = require('web_editor.base');
    var tour = require("web_tour.tour");

    tour.register('website_hr_recruitment_tour', {
        test: true,
        url: '/jobs/apply/3',
        wait_for: base.ready(),
    }, [{
        content: "Complete name",
        trigger: "input[name=partner_name]",
        run: "text John Smith"
    }, {
        content: "Complete Email",
        trigger: "input[name=email_from]",
        run: "text john@smith.com"
    }, {
        content: "Complete phone number",
        trigger: "input[name=partner_phone]",
        run: "text 118.218"
    }, {
        content: "Complete Subject",
        trigger: "textarea[name=description]",
        run: "text ### HR RECRUITMENT TEST DATA ###"
    }, { // TODO: Upload a file ?
        content: "Send the form",
        trigger: ".o_website_form_send"
    }, {
        content: "Check the form is submited without errors",
        trigger: ".oe_structure:has(h1:contains('Thank you!'))"
    }]);

    return {};
});
