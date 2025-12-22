/** @odoo-module **/

import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

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
            trigger: 'div[name="body_arch"] :iframe #default',
            content: markup('Choose this <b>theme</b>.'),
            run: 'click',
        }, {
            trigger: '.o_codeview_btn',
            content: markup('Click here to switch to <b>code view</b>'),
            run: 'click'
        }, {
            trigger: ':iframe .o_codeview',
            content: ('Remove all content from codeview'),
            run: function () {
                const iframe = document.querySelector('.wysiwyg_iframe');
                const iframeDocument = iframe.contentWindow.document;
                let element = iframeDocument.querySelector(".o_codeview");
                element.value = '';
            }
        }, {
            trigger: '.o_codeview_btn',
            content: markup('Click here to switch back from <b>code view</b>'),
            run: 'click'
        }, {
            trigger: '[name="body_arch"] :iframe .o_mail_wrapper_td',
            content: 'Verify that the dropable zone was not removed',
        }, {
            trigger: '[name="body_arch"] #email_designer_body_elements [name="Title"] .oe_snippet_thumbnail',
            content: 'Drag the "Title" snippet from the design panel and drop it in the editor',
            async run(helpers) {
                helpers.drag_and_drop(`[name="body_arch"] :iframe .o_editable`, {
                    position: {
                        top: 340,
                    }
                });
            }
        }, {
            trigger: '[name="body_arch"] :iframe .o_editable h1',
            content: 'Verify that the title was inserted properly in the editor',
        },
        ...stepUtils.discardForm(),
    ]
});
