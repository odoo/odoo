import { registry } from "@web/core/registry";
import { contains, insertText } from "@web/../tests/utils";

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
            trigger: "[data-menu=settings]",
            run: "click",
        },
        {
            content: "Update the email address",
            trigger: 'div[name="email"] input',
            async run() {
                await insertText("div[name='email'] input", "updatedemail@example.com", {
                    replace: true,
                });
                await contains(".o_form_dirty", { count: 1 });
            },
        },
        {
            trigger: "body.modal-open",
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
