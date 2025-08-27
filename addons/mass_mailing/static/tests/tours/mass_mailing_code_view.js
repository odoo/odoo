import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('mass_mailing_code_view_tour', {
    url: '/odoo?debug=tests',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
            run: "click",
        }, {
            trigger: 'button.o_list_button_add',
            run: "click",
        }, {
            trigger: 'input#subject_0',
            content: markup('Pick the <b>email subject</b>.'),
            tooltipPosition: 'bottom',
            run: "edit Test",
        }, {
            trigger: 'div[name="contact_list_ids"] .o_input_dropdown input[type="text"]',
            content: 'Click on the dropdown to open it and then start typing to search.',
            run: "edit Test"
        }, {
            trigger: 'div[name="contact_list_ids"] .ui-state-active',
            content: 'Select item from dropdown',
            run: 'click',
        }, {
            trigger: 'div[name="body_arch"] .o_mailing_template_preview_wrapper [data-name="default"]',
            content: markup('Choose this <b>theme</b>.'),
            run: 'click',
        }, {
            trigger: '.o_codeview_btn',
            content: markup('Click here to switch to <b>code view</b>'),
            run: 'click'
        }, {
            trigger: "textarea.o_codeview",
            content: "Remove all content from codeview",
            run: function () {
                const element = document.querySelector(".o_codeview");
                element.value = "";
            },
        }, {
            trigger: '.o_codeview_btn',
            content: markup('Click here to switch back from <b>code view</b>'),
            run: 'click'
        }, {
            trigger: '[name="body_arch"] :iframe .o_mail_wrapper_td',
            content: 'Verify that the dropable zone was not removed',
        }, {
            trigger: ".o_builder_sidebar_open",
            content: "Wait for the html_builder to be visible",
        }, {
            trigger: '.o_snippet[name="Headings"] button',
            content: 'Click the "Headings" snippet category to drop a snippet in the editor',
            run: "click",
        },
        {
            trigger: ".modal-body :iframe .o_snippet_preview_wrap:has(.s_title)",
            content: "Select the Title Snippet",
            run: "click",
        },
        {
            trigger: '[name="body_arch"] :iframe .o_editable h1',
            content: 'Verify that the title was inserted properly in the editor',
        },
        ...stepUtils.discardForm(),
    ]
});
