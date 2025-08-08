import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("mail/static/tests/tours/mail_composer_autosave_tour.js", {
    steps: () => [
        {
            content: "Edit the function field",
            trigger: ".o_field_widget[name='function'] > .o_input",
            run: "edit Director",
        },
        {
            trigger: ".o_form_sheet_bg",
            run: "click",
        },
        {
            content: "Click on Send Message",
            trigger: ".o-mail-Chatter-sendMessage",
            run: "click",
        },
        {
            content: "Open the full composer",
            trigger: "[name='open-full-composer']",
            run: "click",
        },
        {
            content: "Edit the body",
            trigger: ".o-wysiwyg div[contenteditable='true']",
            run: "editor Hello-- Mitchell Admin",
        },
        {
            content: "Click on Send Message",
            trigger: ".o_mail_send[name='action_send_mail']",
            run: "click",
        },
        {
            content: "Check message is shown",
            trigger: '.o-mail-Message-body:contains("Hello")',
        },
        {
            trigger: ".o_form_saved",
        },
        ...stepUtils.toggleHomeMenu(),
    ],
});
