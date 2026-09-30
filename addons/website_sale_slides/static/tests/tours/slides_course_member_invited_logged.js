import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("invited_on_payment_course_logged", {
    steps: () => [
        {
            trigger: 'a:contains("Add to Cart")',
            content: "Check that the course can be bought but not joined",
            run: function () {
                if (document.querySelector(".o_wslides_js_course_join_link")) {
                    console.error("The course should not be joinable before buying");
                }
            },
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
            trigger: '.o_wslides_slides_list_slide:contains("Home Gardening")',
            content: "Check that non-preview slides are not accessible",
            run: function () {
                if (this.anchor.querySelector(".o_wslides_js_slides_list_slide_link")) {
                    console.error("Invited attendee should not access non-preview slides");
                }
            },
        },
        {
            trigger: 'a:contains("Gardening: The Know-How")',
            content: "Check that preview slides are accessible",
        },
    ],
});
