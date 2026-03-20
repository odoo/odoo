import { registerWebsitePreviewTour } from "@website/js/tours/tour_utils";

/**
 * Global use case:
 * a user (either employee, website restricted editor or portal) joins a public
 *  course;
 * they have access to the full course content when they are a member of the
 *  course;
 * they use fullscreen player to complete the course;
 * they rate the course;
 */
registerWebsitePreviewTour(
    "course_member_youtube",
    {
        url: "/slides",
        edition: false,
    },
    () => [
        // eLearning: go on /all, find free course and join it
        {
            trigger: ":iframe a.o_wslides_home_all_slides",
            run: "click",
        },
        {
            trigger: ':iframe a:contains("Choose your wood")',
            run: "click",
        },
        {
            trigger: ':iframe a:contains("Join this Course")',
            run: "click",
        },
        {
            // check membership
            trigger: ':iframe .o_wslides_js_course_join:contains("You\'re enrolled")',
        },
        {
            trigger: ':iframe a:contains("Comparing Hardness of Wood Species")',
            run: "click",
        },
        {
            // check progression
            trigger: ':iframe .o_wslides_progress_percentage:contains("50")',
        },
        {
            trigger: ':iframe .o_wslides_fs_slide_name:contains("Wood Bending With Steam Box")',
            run: "click",
        },
        {
            // check player loading
            trigger: ":iframe .player",
        },
        {
            // check that video slide is marked as 'done'
            trigger:
                ':iframe .o_wslides_fs_sidebar_section_slides li:contains("Wood Bending With Steam Box") .o_wslides_slide_completed',
        },
        {
            // check progression
            trigger: ":iframe .o_wslides_channel_completion_completed:contains(Completed)",
        },
        {
            trigger: ':iframe a:contains("Back to course")',
            run: "click",
        },
    ]
);
