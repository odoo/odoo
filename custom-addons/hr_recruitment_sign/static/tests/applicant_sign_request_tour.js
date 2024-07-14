/** @odoo-module **/
    
    import { registry } from "@web/core/registry";

    registry.category("web_tour.tours").add('applicant_sign_request_tour', {
            test: true,
            url: '/web',
            steps: () => [
            {
                content: "Access on the recruitment app",
                trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
                run: 'click',
            },
            {
                content: "Go on applications",
                trigger: '.dropdown-toggle[data-menu-xmlid="hr_recruitment.menu_crm_case_categ0_act_job"]',
                run: 'click',
            },
            {
                content: "Go on all applications",
                trigger: 'a[data-menu-xmlid="hr_recruitment.menu_crm_case_categ_all_app"]',
                run: 'click',
            },
            {
                content: "Open group",
                trigger: 'tr.o_group_has_content:contains("None")',
                run: 'click',
            },
            {
                content: "Open Saitama's application",
                trigger: '.o_data_cell[data-tooltip="Saitama"]',
                run: 'click',
            },
            {
                trigger: ".o_statusbar_status button.dropdown-toggle",
                content: "Move applicant to hired stage",
                run: 'click'
            },
            {
                content: "Recruitment",
                trigger: '.dropdown-item:contains("Contract Signed")',
                run: 'click',
            },
            {
                content: "Create an employee",
                trigger: '.btn[name="create_employee_from_applicant"]',
                run: 'click',
            },
            {
                content: "Validate the creation",
                trigger: '.btn.o_form_button_save',
                extra_trigger: '.o_hr_employee_form_view',
                run: 'click',
            },
            {
                content: "Validate the creation",
                trigger: '.o_menu_brand',
                extra_trigger: '.o_form_status_indicator_buttons.invisible',
                run: 'click',
            },
        ]
    });
