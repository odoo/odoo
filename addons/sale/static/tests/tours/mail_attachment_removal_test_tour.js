import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("mail_attachment_removal_tour", {
    steps: () => [

    {
        content: "click on send by email",
        trigger: ".o_statusbar_buttons > button[name='action_quotation_send']",
        run: "click"
    },
    {
        content: "save a new layout",
        trigger: ".o_technical_modal button[name='document_layout_save']",
        run: "click"
    },
    {
        content: "delete attachment",
        trigger: ".o_field_widget[name='attachment_ids'] li > button .fa-times",
        run: "click"
    },
    {
        content: "send the email",
        trigger: ".o_mail_send",
        run: "click"
    },
    {
        content: "confirm quotation",
        trigger: "button[name='action_confirm']",
        run: "click"
    }
]
})
