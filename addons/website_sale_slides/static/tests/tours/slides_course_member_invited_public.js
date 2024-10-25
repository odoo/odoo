import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("invited_on_payment_course_public", {
    steps: () => [
        {
            isActive: ["body:has(.modal:not(.o_inactive_modal):contains(oops))"],
            content: "Close Oops modal",
            trigger: ".modal button:contains(close)",
            run: "click",
        },
        {
            trigger: '.o_wslides_identification_banner a:contains("Log in")',
            content: "Check that there is an identification banner",
        },
        {
            trigger: '.o_wslides_js_course_join a:contains("Log in")',
            run: function () {
                if (document.querySelector(".o_wslides_js_course_join #add_to_cart")) {
                    console.error("The course should not be buyable before logging in");
                }
            },
        },
        {
            trigger: '.o_wslides_slides_list_slide:contains("Gardening: The Know-How")',
            run: function () {
                if (this.anchor.querySelector(".o_wslides_js_slides_list_slide_link")) {
                    console.error("Invited attendee should not access slides, even previews");
                }
            },
        },
        {
            trigger: 'a:contains("Log in")',
            run: "click",
        },
        {
            trigger: 'input[id="password"]',
            run: "edit portal",
        },
        {
            trigger: 'button:contains("Log in")',
            run: "click",
        },
        {
            trigger: 'a:contains("Gardening: The Know-How")',
            content: "Check that preview slides are now accessible",
        },
        // Chatter is lazy loading. Wait for it.
        {
            trigger: "a[id=review-tab]",
            run: "click",
        },
        {
            content: "Wait for the whole page to load",
            trigger: "#chatterRoot:shadow .o-mail-Chatter",
        },
        {
            trigger: "a[id=home-tab]",
            run: "click",
        },
        {
            trigger: '.o_wslides_js_course_join:contains("Add to Cart")',
            content: "Check that the course can now be bought",
        },
    ],
});
