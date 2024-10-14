import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("invite_check_channel_preview_as_public", {
    steps: () => [
        {
            trigger: ".o_wslides_identification_banner",
            content: "Check that there is an identification banner",
        },
        {
            trigger: '.o_wslides_slides_list_slide:contains("Gardening: The Know-How")',
            run: function () {
                if (this.anchor.querySelector(".o_wslides_js_slides_list_slide_link")) {
                    console.error("The preview should not allow the public user to browse slides");
                }
            },
        },
        {
            trigger: 'a:contains("Join this Course")',
            run: "click",
        },
        {
            trigger: 'a:contains("login")',
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
            trigger: 'a:contains("Join this Course")',
            run: "click",
        },
        {
            trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
            content: "Check that user is enrolled",
        },
        {
            trigger: '.o_wslides_js_slides_list_slide_link:contains("Gardening: The Know-How")',
            content: "Check that slides are now accessible",
        },
    ],
});
