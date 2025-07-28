import { delay } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

/**
 * Global use case:
 * an user (either employee, website restricted editor or portal) joins a public
    course;
 * they have access to the full course content when they are a member of the
    course;
 * they use fullscreen player to complete the course;
 * they rate the course;
 */
registry.category("web_tour.tours").add("course_member", {
    url: "/slides",
    steps: () => [
        // eLearning: go on free course and join it
        {
            trigger: 'a:contains("Basics of Gardening - Test")',
            run: "click",
            expectUnloadPage: true,
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
            expectUnloadPage: true,
        },
        {
            // check membership
            trigger: '.o_wslides_js_course_join:contains("You\'re enrolled")',
        },
        {
            trigger: 'a:contains("Gardening: The Know-How")',
            run: "click",
            expectUnloadPage: true,
        },
        // eLearning: follow course by cliking on first lesson and going to fullscreen player
        {
            trigger: '.o_wslides_fs_slide_name:contains("Home Gardening")',
            run: "click",
        },
        // eLearning: share the first slide
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
            // check email has been sent
            trigger: '.o_wslides_js_share_email:contains("Sharing is caring")',
        },
        {
            trigger: '.modal-footer button:contains("Close")',
            run: "click",
        },
        // eLeaning: course completion
        {
            trigger: ".o_wslides_fs_sidebar_header",
            run: "press ArrowLeft",
        },
        {
            trigger: ".o_wslides_fs_sidebar_list_item.active:contains(Gardening: The Know-How)",
        },
        {
            trigger: '.o_wslides_progress_percentage:contains("40")',
            run: "press ArrowRight",
        },
        {
            trigger: ".o_wslides_fs_sidebar_list_item.active:contains(Home Gardening)",
        },
        {
            // check progression
            trigger: '.o_wslides_progress_percentage:contains("40")',
            run: "press ArrowRight",
        },
        {
            trigger: ".o_wslides_fs_sidebar_list_item.active:contains(Mighty Carrots)",
        },
        {
            // check progression
            trigger: '.o_wslides_progress_percentage:contains("60")',
        },
        {
            trigger:
                '.o_wslides_fs_slide_name:contains("How to Grow and Harvest The Best Strawberries | Basics")',
            run: "click",
        },
        {
            // check that video slide is marked as 'done'
            trigger:
                '.o_wslides_fs_sidebar_section_slides li:contains("How to Grow and Harvest The Best Strawberries | Basics") .o_wslides_slide_completed',
        },
        {
            // check progression
            trigger: '.o_wslides_progress_percentage:contains("80")',
        },
        // eLearning: last slide is a quiz, complete it
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
            // check that we have a properly motivational message to motivate us!
            trigger:
                '.o_wslides_quiz_modal_rank_motivational > div > div:contains("Reach the next rank and gain a very nice mug!")',
            run: "click",
        },
        {
            trigger: 'a:contains("End course")',
            run: "click",
            expectUnloadPage: true,
        },
        // eLearning: ending course redirect to /slides, course is completed now
        {
            // check that the course is marked as completed
            trigger: 'div:contains("Basics of Gardening") span:contains("Completed")',
        },
        // eLearning: go back on course and rate it
        {
            trigger: 'a:contains("Basics of Gardening")',
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: 'button[data-bs-target="#ratingpopupcomposer"]:contains("Add Review")',
            run: "click",
        },
        {
            trigger: ".modal.modal_shown .modal-body i.fa.fa-star:eq(2)",
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
        // eLearning: edit the review
        {
            trigger: 'button[data-bs-target="#ratingpopupcomposer"]:contains("Edit Review")',
            run: "click",
        },
        {
            trigger: ".modal.modal_shown .modal-body i.fa.fa-star-o:eq(1)",
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
