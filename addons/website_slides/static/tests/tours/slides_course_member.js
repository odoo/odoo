import { delay } from "@web/core/utils/concurrency";
import { registry } from "@web/core/registry";

function checkSidebarListItemIsCompleted(contains) {
    return {
        trigger: `.o_wslides_fs_sidebar_list_item.active:contains(${contains}):has(.o_wslides_button_complete)`,
    };
}

function checkProgressBar(pc) {
    return {
        content: `check progression is ${pc}%`,
        trigger: `.o_wslides_channel_completion_progressbar:has(.progress-bar[style*="width: ${pc}%"]):has(.o_wslides_progress_percentage:contains(${pc}))`,
    };
}

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
        checkSidebarListItemIsCompleted("Gardening: The Know-How"),
        checkProgressBar(20),
        {
            trigger: '.o_wslides_fs_slide_name:contains("Home Gardening")',
            run: "click",
        },
        checkSidebarListItemIsCompleted("Home Gardening"),
        checkProgressBar(40),
        // eLearning: share the first slide
        {
            trigger: ".o_wslides_share",
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
        checkSidebarListItemIsCompleted("Gardening: The Know-How"),
        checkProgressBar(40),
        {
            trigger: ".o_wslides_fs_sidebar_header",
            run: "press ArrowRight",
        },
        checkSidebarListItemIsCompleted("Home Gardening"),
        checkProgressBar(40),
        {
            trigger: ".o_wslides_fs_sidebar_header",
            run: "press ArrowRight",
        },
        checkSidebarListItemIsCompleted("Mighty Carrots"),
        checkProgressBar(60),
        {
            trigger:
                '.o_wslides_fs_slide_name:contains("How to Grow and Harvest The Best Strawberries | Basics")',
            async run({ click }) {
                // TODO: remove this delay
                await delay(500);
                await click();
            },
        },
        checkSidebarListItemIsCompleted("How to Grow and Harvest The Best Strawberries | Basics"),
        checkProgressBar(80),
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
        checkSidebarListItemIsCompleted("Test your knowledge"),
        {
            content: "check that we have a properly motivational message to motivate us!",
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
            content: "check that the course is marked as completed",
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
            run: "click",
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
