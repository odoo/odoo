/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('mailing_editor', {
    url: '/odoo',
    steps: () => [stepUtils.showAppsMenuItem(), {
    trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
    run: "click",
}, {
    trigger: 'button.o_list_button_add',
    run: "click",
}, {
    trigger: 'div[name="contact_list_ids"] .o_input_dropdown input[type="text"]',
    run: "edit Test",
}, {
    trigger: 'div[name="contact_list_ids"] .ui-state-active',
    run: "click",
}, {
    content: 'choose the theme "empty" to edit the mailing with snippets',
    trigger: '[name="body_arch"] :iframe #empty',
    run() {
        this.anchor.click();
    }
}, {
    content: 'wait for the editor to be rendered',
    trigger: '[name="body_arch"] :iframe .o_editable[data-editor-message="DRAG BUILDING BLOCKS HERE"]',
}, {
    content: 'drag the "Title" snippet from the design panel and drop it in the editor',
    trigger: '[name="body_arch"] #oe_snippets [name="Title"] .oe_snippet_thumbnail',
    async run(helpers) {
        await helpers.drag_and_drop(`[name="body_arch"] :iframe .o_editable`, {
            position: {
                top: 340,
            },
        });
    },
}, {
    content: 'wait for the snippet menu to finish the drop process',
    trigger: 'body:not(:has(.o_we_ongoing_insertion))',
}, {
    content: 'verify that the title was inserted properly in the editor',
    trigger: '[name="body_arch"] :iframe .o_editable h1',
}, {
    trigger: 'button.o_form_button_save',
    run: "click",
}, {
    content: 'verify that the save failed (since the field "subject" was not set and it is required)',
    trigger: 'label.o_field_invalid',
}, {
    content: 'verify that the edited mailing body was not lost during the failed save',
    trigger: '[name="body_arch"] :iframe .o_editable h1',
}, {
    trigger: 'input#subject_0',
    run: "edit TestFromTour",
}, {
    trigger: '.o_form_view', // blur previous input
    run: "click",
},
...stepUtils.saveForm(),
{
    trigger: ':iframe .o_editable',
}]});
