import { registry } from "@web/core/registry";
import { click, contains } from "@web/../tests/utils";

/**
 * Verify that a user can modify their own profile information.
 */
registry.category("web_tour.tours").add("mail/static/tests/tours/user_modify_own_profile_tour.js", {
    steps: () => [
        {
            content: "Open user account menu",
            trigger: ".o_user_menu button",
            run: "click",
        },
        {
            content: "Open preferences / profile screen",
            trigger: "[data-menu=preferences]",
            run: "click",
        },
        {
            content: "Update the notification type",
            trigger: '.modal div[name="notification_type"] input[data-value="inbox"]',
            async run() {
                await click('.modal div[name="notification_type"] input[data-value="inbox"]');
                await contains(".o_form_dirty", { count: 1 });
            },
        },
        {
            content: "Save the form",
            trigger: 'button[name="preference_save"]',
            run: "click",
        },
        {
            content: "Wait until the modal is closed",
            trigger: "body:not(.modal-open)",
            async run() {
                await contains(".o_form_dirty", { count: 0 });
            },
        },
    ],
});
