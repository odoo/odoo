import { registry } from "@web/core/registry";
import { session } from "@web/session";

registry.category("web_tour.tours").add("email_reminder_tour", {
    steps: () => (function () {
        let steps = [
            {
                content: "Click on favorite button",
                trigger: "button:contains('Add to favorite')",
                run: "click",
            },
        ];
        if (session.is_public) {
            steps = steps.concat([{
                content: "The form is filled",
                trigger: "#o_wetrack_email_reminder_form input[name='email']",
                run: "fill visitor@odoo.com",
            },
            {
                content: "The form is submit",
                trigger: "#o_wetrack_email_reminder_form button[type='submit']",
                run: "click",
            }]);
        }
        steps = steps.concat([{
            content: `Check Favorite is now on`,
            trigger: "div.o_wetrack_js_reminder button.o_wetrack_js_reminder_on",
        }]);
        return steps;
    })()
});
