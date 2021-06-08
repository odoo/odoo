odoo.define("website_event_booth_exhibitor.tour", function (require) {
    "use strict";

    var core = require("web.core");
    var tour = require("web_tour.tour");

    var _t = core._t;

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
        trigger: 'img[title="Premium Booth"]',
    }, {
        contnet: 'Choose Booth',
        trigger: 'div:contains("OpenWood Demonstrator 2") input',
    }, {
        content: "Validate attendees details",
        // extra_trigger: "input[name='1-name'], input[name='2-name'], input[name='3-name']",
        trigger: 'button:contains("Fill Sponsor Details")',
        run: 'click',
    }, {
        content: "Fill booth details",
        trigger: 'form[id="contact_details_form"]',
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
        trigger: 'button:contains("Book My Booth")',
        run: 'click',
    },  {
        trigger: 'h3:contains("Booth Registration Completed")',
        run: function() {},
    }
    ]);
});
