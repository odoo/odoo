import { registry } from "@web/core/registry";
import { session } from "@web/session";

registry.category("web_tour.tours").add("email_reminder_tour", {
    steps: () => (function () {
        let steps = [
            {
                content: "Click on favorite button",
                trigger: "i[title='Set Favorite']",
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
            content: "Check if the notification is displayed.",
            trigger: "div.o_send_email_reminder_success",
        }]);
        return steps;
    })()
});
