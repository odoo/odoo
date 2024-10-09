/** @odoo-module **/
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category('web_tour.tours').add('mailing_campaign', {
    url: '/odoo',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Select the "Email Marketing" app',
            trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
            run: "click",
        },
        {
            content: 'Select "Campaings" Navbar item',
            trigger: '.o_nav_entry[data-menu-xmlid="mass_mailing.menu_email_campaigns"]',
            run: "click",
        },
        {
            content: 'Select "Newsletter" campaign',
            trigger: '.o_kanban_record:contains("Newsletter")',
            run: "click",
        },
        {
            content: 'Add a line (create new mailing)',
            trigger: '.o_field_x2many_list_row_add a',
            run: "click",
        },
        {
            content: 'Pick the basic theme',
            trigger: ":iframe #basic",
            run: "click",
        },
        {
            content: 'Fill in Subject',
            trigger: '#subject_0',
            run: "edit TestFromTour",
        },
        {
            content: 'Fill in Mailing list',
            trigger: '#contact_list_ids_0',
            run: "edit Newsletter",
        },
        {
            content: 'Pick "Newsletter" option',
            trigger: '.o_input_dropdown a:contains(Newsletter)',
            run: "click",
        },
        {
            content: 'Save form',
            trigger: ".modal .o_form_button_save:contains(Save & Close)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            content: 'Check that newly created record is on the list',
            trigger: '[name="mailing_mail_ids"] td[name="subject"]:contains("TestFromTour")',
        },
        ...stepUtils.saveForm(),
    ],
});
