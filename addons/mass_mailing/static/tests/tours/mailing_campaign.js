/** @odoo-module **/
    
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category('web_tour.tours').add('mailing_campaign', {
    test: true,
    url: '/web',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Select the "Email Marketing" app',
            trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
        },
        {
            content: 'Select "Campaings" Navbar item',
            trigger: '.o_nav_entry[data-menu-xmlid="mass_mailing.menu_email_campaigns"]',
        },
        {
            content: 'Select "Newsletter" campaign',
            trigger: '.oe_kanban_card:contains("Newsletter")',
        },
        {
            content: 'Add a line (create new mailing)',
            trigger: '.o_field_x2many_list_row_add a',
        },
        {
            content: 'Pick the basic theme',
            trigger: 'iframe',
            run(actions) {
                // For some reason the selectors inside the iframe cannot be triggered.
                const link = this.$anchor[0].contentDocument.querySelector('#basic');
                actions.click(link);
            }
        },
        {
            content: 'Fill in Subject',
            trigger: '#subject_0',
            run: 'text TestFromTour',
        },
        {
            content: 'Fill in Mailing list',
            trigger: '#contact_list_ids_0',
            run: 'text Newsletter',
        },
        {
            content: 'Pick "Newsletter" option',
            trigger: '.o_input_dropdown a:contains(Newsletter)',
        },
        {
            content: 'Save form',
            trigger: '.o_form_button_save',
        },
        {
            content: 'Check that newly created record is on the list',
            trigger: '[name="mailing_mail_ids"] td[name="subject"]:contains("TestFromTour")',
            run: () => null,
        },
        ...stepUtils.saveForm(),
    ]
});
