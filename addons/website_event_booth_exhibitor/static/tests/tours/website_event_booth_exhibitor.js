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
        trigger: 'a:contains("Become exhibitor")',
        run: "click",
        expectUnloadPage: true,
    }, {
        content: 'Wait for the first item to be properly selected before proceeding',
        trigger: 'label.d-block:has(input:checked) h5[name=booth_category_name]',
    }, {
        content: 'Choose Premium Booths',
        trigger: 'img[alt="Premium Booth"]',
        run: "click",
    }, {
        content: 'Choose Booth',
        trigger: ".o_wbooth_booths div:contains(OpenWood Demonstrator 2) input:not(:visible)",
        run: "click",
    }, {
        content: "Validate attendees details",
        trigger: 'button:enabled:contains("Book my Booth(s)")',
        run: 'click',
        expectUnloadPage: true,
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
    },
    {
        trigger: "input[name='sponsor_name'], input[name='sponsor_email'], input[name='sponsor_phone']",
    }, ...new FinalSteps()._getSteps()].filter(Boolean)});
