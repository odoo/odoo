odoo.define('website_crm.tour', function(require) {
    'use strict';

    var tour = require('web_tour.tour');

    tour.register('website_crm_tour', {
        test: true,
        url: '/contactus',
    }, [{
        content: "Complete name",
        trigger: "input[name=contact_name]",
        run: "text John Smith",
    }, {
        content: "Complete phone number",
        trigger: "input[name=phone]",
        run: "text +32 485 118.218"
    }, {
        content: "Complete Email",
        trigger: "input[name=email_from]",
        run: "text john@smith.com"
    }, {
        content: "Complete Company",
        trigger: "input[name=partner_name]",
        run: "text Odoo S.A."
    }, {
        content: "Complete Subject",
        trigger: "input[name=name]",
        run: "text Useless message"
    }, {
        content: "Complete Subject",
        trigger: "textarea[name=description]",
        run: "text ### TOUR DATA ###"
    }, {
        content: "Send the form",
        trigger: ".o_website_form_send"
    }, {
        content: "Check we were redirected to the success page",
        trigger: "#wrap:has(h1:contains('Thanks')):has(div.alert-success)"
    }]);

    return {};
});
