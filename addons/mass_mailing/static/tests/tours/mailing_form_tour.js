import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("mailing_form_tour", {
    steps: () => [
        // Mailing form: received ratio widget
        {
            content: "Received ratio widget shows its top field",
            trigger: ".o_form_view div[name='received_ratio'] .o_pie_text:contains(Delivered)",
        },
        {
            content: "Received ratio widget shows its bottom field",
            trigger: ".o_form_view div[name='received_ratio'] .o_pie_text:contains(Failed)",
        },
        {
            content: "Go to a new mailing filter form",
            trigger: ".o_form_view div[name='received_ratio']",
            run() {
                window.location.href = "/odoo/action-mass_mailing.mailing_filter_action/new";
            },
            expectUnloadPage: true,
        },
        // Mailing filter form: domain widget
        {
            content: "Set the list name",
            trigger: ".o_form_view div[name='name'] textarea",
            run: "edit Test Dynamic List",
        },
        {
            content: "Set the recipients model",
            trigger: ".o_form_view div[name='mailing_model_id'] input",
            run: "edit Mailing Contact",
        },
        {
            content: "Select it",
            trigger: ".o-autocomplete--dropdown-item .dropdown-item:contains(Mailing Contact)",
            run: "click",
        },
        {
            content: "Domain widget resolved the model and fetched the record count",
            trigger: ".o_form_view div[name='mailing_domain'] .o_domain_show_selection_button",
        },
        ...stepUtils.saveForm(),
    ],
});
