odoo.define("website_event_booth_exhibitor.tour_steps", function (require) {
    "use strict";

    var core = require('web.core');

    var FinalSteps = core.Class.extend({

        _getSteps: function () {
            return [{
                trigger: 'h3:contains("Booth Registration completed!")',
                run: function() {},
            }];
        },

    });

    return FinalSteps;

});
odoo.define("website_event_booth_exhibitor.tour", function (require) {
    "use strict";

    var tour = require("web_tour.tour");
    var FinalSteps = require('website_event_booth_exhibitor.tour_steps');


    tour.register("webooth_exhibitor_register", {
        test: true,
        url: "/event",
    }, [{
        content: 'Go on "Online Reveal" page',
        trigger: 'a[href*="/event"]:contains("Online Reveal"):first',
    }, {
        content: 'Browse Booths',
        trigger: 'a:contains("Get A Booth")',
    }, {
        content: 'Choose Premium Booths',
        trigger: 'img[alt="Premium Booth"]',
    }, {
        content: 'Choose Booth',
        trigger: '.o_wbooth_booths div:contains("OpenWood Demonstrator 2") input',
    }, {
        content: "Validate attendees details",
        trigger: 'button:contains("Book my Booths")',
        run: 'click',
    }, {
        content: "Fill booth details",
        trigger: 'form[id="o_wbooth_contact_details_form"]',
        run: function () {
            $("input[name='sponsor_name']").val("Patrick Sponsor");
            $("input[name='sponsor_email']").val("patrick.sponssor@test.example.com");
            $("input[name='sponsor_phone']").val("+32456001122");
            $("input[name='sponsor_slogan']").val("Patrick is Your Sponsor");
            $("textarea[name='sponsor_description']").text("Really eager to meet you !");
        },
    }, {
        content: "Validate booth details",
        extra_trigger: "input[name='sponsor_name'], input[name='sponsor_email'], input[name='sponsor_phone']",
        trigger: 'button:contains("Book my Booths")',
        run: 'click',
    }, ...new FinalSteps()._getSteps()].filter(Boolean));
});
