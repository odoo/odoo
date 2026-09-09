import { registry } from "@web/core/registry";
import { delay } from "@web/core/utils/concurrency";

registry.category("web_tour.tours").add("course_member", {
    url: "/slides",
    steps: () => [
        {
            trigger: 'a:contains("Basics of Gardening - Test")',
            run: "click",
            expectUnloadPage: true,
        },
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
            expectUnloadPage: true,
        },
        {
            trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
        },
        {
            trigger: 'a:contains("Gardening: The Know-How")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: '.o_wslides_fs_slide_name:contains("Home Gardening")',
            run: "click",
        },
        {
            trigger: ".o_wslides_fs_share",
            run: "click",
        },
        {
            trigger: ".o_wslides_js_share_email input",
            run: "edit friend@example.com",
        },
        {
            trigger: ".o_wslides_js_share_email button",
            run: "click",
        },
        {
            trigger: '.o_wslides_js_share_email:contains("Sharing is caring")',
        },
        {
            trigger: '.modal-footer button:contains("Close")',
            run: "click",
        },
        {
            trigger: ".o_wslides_fs_sidebar_header",
            run: "press ArrowLeft",
        },
        {
            trigger:
                ".o_wslides_fs_sidebar_list_item.active:contains(Gardening: The Know-How)",
        },
        {
            trigger: '.o_wslides_progress_percentage:contains("40")',
            run: "press ArrowRight",
        },
        {
            trigger: ".o_wslides_fs_sidebar_list_item.active:contains(Home Gardening)",
        },
        {
            trigger: '.o_wslides_progress_percentage:contains("40")',
            run: "press ArrowRight",
        },
        {
            trigger: ".o_wslides_fs_sidebar_list_item.active:contains(Mighty Carrots)",
        },
        {
            trigger: '.o_wslides_progress_percentage:contains("60")',
        },
        {
            trigger:
                '.o_wslides_fs_slide_name:contains("How to Grow and Harvest The Best Strawberries | Basics")',
            run: "click",
        },
        {
            trigger:
                '.o_wslides_fs_sidebar_section_slides li:contains("How to Grow and Harvest The Best Strawberries | Basics") .o_wslides_slide_completed',
        },
        {
            trigger: '.o_wslides_progress_percentage:contains("80")',
        },
        {
            trigger: '.o_wslides_fs_slide_name:contains("Test your knowledge")',
            run: "click",
        },
        {
            trigger: ".o_wslides_js_lesson_quiz_question:first .list-group a:first",
            run: "click",
        },
        {
            trigger: ".o_wslides_js_lesson_quiz_question:last .list-group a:first",
            run: "click",
        },
        {
            trigger: ".o_wslides_js_lesson_quiz_submit",
            run: "click",
        },
        {
            trigger:
                '.o_wslides_quiz_modal_rank_motivational > div > div:contains("Reach the next rank and gain a very nice mug!")',
            run: "click",
        },
        {
            trigger: 'a:contains("End course")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: 'div:contains("Basics of Gardening") span:contains("Completed")',
        },
        {
            trigger: 'a:contains("Basics of Gardening")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger:
                'button[data-bs-target="#ratingpopupcomposer"]:contains("Add Review")',
            run: "click",
        },
        {
            trigger: ".modal.modal_shown .modal-body .o-mail-Composer-stars i:eq(2)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown .modal-body textarea",
            run: "edit This is a great course. Top!",
        },
        {
            trigger: ".modal.modal_shown button:contains(review)",
            run: "click",
        },
        {
            content: "Wait the first review is closed before send the second",
            trigger: "body:not(:has(.modal:visible))",
        },
        {
            trigger: "span:contains(Edit Review)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown .modal-body .o-mail-Composer-stars i:eq(4)",
            run: "click",
        },
        {
            trigger: ".modal.modal_shown .modal-body textarea",
            run: "edit This is a great course. I highly recommend it!",
        },
        {
            trigger: ".modal.modal_shown button:contains(review)",
            async run(helpers) {
                await delay(500);
                await helpers.click();
            },
        },
        {
            trigger: 'a[id="review-tab"]',
            run: "click",
        },
        {
            trigger:
                "#chatterRoot:shadow .o-mail-Message:contains('This is a great course. I highly recommend it!')",
        },
    ],
});
