/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import FinalSteps from "@website_event_booth_exhibitor/../tests/tours/website_event_booth_exhibitor_steps";


    registry.category("web_tour.tours").add("webooth_exhibitor_register", {
        test: true,
        url: "/event",
        steps: () => [{
        content: 'Go on "Online Reveal" page',
        trigger: 'a[href*="/event"]:contains("Online Reveal"):first',
    }, {
        content: 'Browse Booths',
        trigger: 'a:contains("Get A Booth")',
    }, {
        content: 'Wait for the first item to be properly selected before proceeding',
        trigger: 'label.d-block:has(input:checked) h5[name=booth_category_name]',
        run() {},
    }, {
        content: 'Choose Premium Booths',
        trigger: 'img[alt="Premium Booth"]',
    }, {
        content: 'Choose Booth',
        trigger: '.o_wbooth_booths div:contains("OpenWood Demonstrator 2") input',
    }, {
        content: "Validate attendees details",
        trigger: 'button:enabled:contains("Book my Booth(s)")',
        run: 'click',
    }, {
        content: "Fill booth details",
        trigger: 'form[id="o_wbooth_contact_details_form"]',
        run: function () {
            document.querySelector("input[name='sponsor_name']").value = "Patrick Sponsor";
            document.querySelector("input[name='sponsor_email']").value = "patrick.sponssor@test.example.com";
            document.querySelector("input[name='sponsor_phone']").value = "+32456001122";
            document.querySelector("input[name='sponsor_slogan']").value = "Patrick is Your Sponsor";
            document.querySelector("textarea[name='sponsor_description']").textContent = "Really eager to meet you !";
        },
    }, {
        content: "Validate booth details",
        extra_trigger: "input[name='sponsor_name'], input[name='sponsor_email'], input[name='sponsor_phone']",
        trigger: 'button.o_wbooth_registration_confirm',
        run: 'click',
    }, ...new FinalSteps()._getSteps()].filter(Boolean)});
