import { registry } from '@web/core/registry';
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category('web_tour.tours').add('section_saved_on_tab_keydown_tour', {
    steps: () => [
        {
            content: "Create new invoice",
            trigger: '.o_control_panel_main_buttons .o_list_button_add',
            run: 'click',
        },
        // Set customer
        {
            content: "Add customer",
            trigger: 'div.o_field_widget.o_field_res_partner_many2one[name="partner_id"] div input',
            run: 'edit Partner A',
        },
        {
            content: "Valid customer",
            trigger: '.ui-menu-item a:contains("Partner A")',
            run: 'click',
        },
        ...stepUtils.saveForm(),
        {
            content: 'Add a section line',
            trigger: '.o_field_x2many_list_row_add a:contains("Add a section")',
            run: 'click',
        },
        {
            content: 'Edit the section label textarea',
            trigger: '.o_field_product_label_section_and_note_cell textarea',
            run() {
                const textarea = this.anchor;
                textarea.focus();
                textarea.value = "Section content";
                textarea.dispatchEvent(new KeyboardEvent('keydown', { key: 'Tab' }));
            },
        },
        ...stepUtils.saveForm(),
    ],
});
