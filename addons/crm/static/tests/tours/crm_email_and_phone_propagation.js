odoo.define('crm.crm_email_and_phone_propagation', function (require) {
    'use strict';

    const tour = require('web_tour.tour');

    tour.register('crm_email_and_phone_propagation_edit_save', {
        test: true,
        url: '/web',
    }, [
        tour.stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
            content: 'open crm app',
        }, {
            trigger: '.o_kanban_record .o_kanban_record_title span:contains(Test Lead Propagation)',
            content: 'Open the first lead',
            run: 'click',
        }, {
            trigger: '.o_form_button_edit',
            extra_trigger: '.o_lead_opportunity_form.o_form_readonly',
            content: 'Edit the lead',
            run: 'click',
        }, {
            trigger: '.o_form_button_save',
            extra_trigger: '.o_form_editable .o_field_widget[name=email_from] input',
            content: 'Save the lead',
            run: 'click',
        }, {
            trigger: '.o_form_readonly',
        },
    ]);

    tour.register('crm_email_and_phone_propagation_remove_email_and_phone', {
        test: true,
        url: '/web',
    }, [
        tour.stepUtils.showAppsMenuItem(),
        {
            trigger: '.o_app[data-menu-xmlid="crm.crm_menu_root"]',
            content: 'open crm app',
        }, {
            trigger: '.o_kanban_record .o_kanban_record_title span:contains(Test Lead Propagation)',
            content: 'Open the first lead',
            run: 'click',
        }, {
            trigger: '.o_form_button_edit',
            content: 'Edit the lead',
            run: 'click',
        }, {
            trigger: '.o_form_editable .o_field_widget[name=email_from] input',
            extra_trigger: '.o_form_editable .o_field_widget[name=phone] input',
            content: 'Remove the email and the phone',
            run: function (action) {
                action.remove_text("", ".o_form_editable .o_field_widget[name=email_from] input");
                action.remove_text("", ".o_form_editable .o_field_widget[name=phone] input");
            },
        }, {
            trigger: '.o_form_button_save',
            // wait the the warning message to be visible
            extra_trigger: '.o_form_sheet_bg .fa-exclamation-triangle:not(.o_invisible_modifier)',
            content: 'Save the lead',
            run: 'click',
        }, {
            trigger: '.o_form_readonly',
        },
    ]);

});
