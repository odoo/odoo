/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";

    registry.category("web_tour.tours").add('crm_email_and_phone_propagation_edit_save', {
        url: '/odoo',
        steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
            content: 'open crm app',
            run: "click",
        }, {
            trigger: '.o_kanban_record:contains(Test Lead Propagation)',
            content: 'Open the first lead',
            run: 'click',
        },
        {
            trigger: ".o_form_editable .o_field_widget[name=email_from] input",
        },
        {
            trigger: ".o_form_button_save:not(:visible)",
            content: 'Save the lead',
            run: 'click',
        },
    ]});
