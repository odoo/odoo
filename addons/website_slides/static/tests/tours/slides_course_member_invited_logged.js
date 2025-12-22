import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("invite_check_channel_preview_as_logged", {
    steps: () => [
        {
            trigger: 'a:contains("Gardening: The Know-How")',
            content: "Check that the previews are accessible",
        },
        {
            trigger: '.o_wslides_slides_list_slide:contains("Home Gardening")',
            content: "Check that other slides are not accessible",
            run: function () {
                if (this.anchor.querySelector(".o_wslides_js_slides_list_slide_link")) {
                    console.error("Invited attendee should not see non-preview slides");
                }
            },
        },
        {
            trigger: 'a:contains("Join this Course")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
            content: "Check that user is enrolled",
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
            trigger: '.o_wslides_js_slides_list_slide_link:contains("Home Gardening")',
            content: "Check that slides are now accessible",
        },
    ],
});
