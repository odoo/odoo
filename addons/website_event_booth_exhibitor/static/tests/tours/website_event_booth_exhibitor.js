/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import FinalSteps from "@website_event_booth_exhibitor/../tests/tours/website_event_booth_exhibitor_steps";


    registry.category("web_tour.tours").add("webooth_exhibitor_register", {
        url: "/event",
        steps: () => [{
        content: 'Go on "Online Reveal" page',
        trigger: 'a[href*="/event"]:contains("Online Reveal"):first',
        run: "click",
        expectUnloadPage: true,
    }, {
        content: 'Browse Booths',
        trigger: 'a:contains("Get A Booth")',
        run: "click",
        expectUnloadPage: true,
    }, {
        content: 'Wait for the first item to be properly selected before proceeding',
        trigger: 'label.d-block:has(input:checked) h5[name=booth_category_name]:contains(standard booth)',
    }, {
        content: 'Choose Premium Booths',
        trigger: 'label:has(img[alt="Premium Booth"])',
        run: "click",
    },{
        trigger:
            "label.d-block:has(input:checked) h5[name=booth_category_name]:contains(premium booth)",
    },
    {
        content: 'Choose Booth',
        trigger: ".o_wbooth_booths label:contains(OpenWood Demonstrator 2)",
        run: "click",
    },
    {
        content: "Validate attendees details",
        trigger: 'button:contains("Book my Booth(s)")',
        run: 'click',
        expectUnloadPage: true,
    },
    {
        content: "Fill booth details",
        trigger: "form[id=o_wbooth_contact_details_form]",
    },
    {
        trigger: "input[name=sponsor_name]",
        run: "edit Patrick Sponsor",
    },
    {
        trigger: "input[name=sponsor_email]",
        run: "edit patrick.sponssor@test.example.com",
    },
    {
        trigger: "input[name=sponsor_phone]",
        run: "edit +32456001122",
    },
    {
        trigger: "input[name=sponsor_slogan]",
        run: "edit Patrick is Your Sponsor",
    },
    {
        trigger: "textarea[name=sponsor_description]",
        run: "edit Really eager to meet you !",
    },
    {
        content: "Validate booth details",
        trigger: 'button.o_wbooth_registration_confirm',
        run: 'click',
    }, ...new FinalSteps()._getSteps()].filter(Boolean)});
