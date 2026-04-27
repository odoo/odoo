/* @odoo-module */

import { registry } from "@web/core/registry";
import { inputFiles } from "@web/../tests/utils";
import { queryOne } from "@odoo/hoot-dom";
import { redirect } from "@web/core/utils/urls";

registry.category("web_tour.tours").add("hr_contract_salary_tour", {
    url: "/my",
    wait_for: Promise.resolve(odoo.__TipTemplateDef),
    steps: () => [
        {
            content: "Go on configurator",
            trigger: ".navbar",
            run: function () {
                redirect("/odoo");
            },
            expectUnloadPage: true,
        },
        {
            content: "Log into Belgian Company",
            trigger: ".o_menu_systray .o_switch_company_menu button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Log into Belgian Company",
            trigger:
                ".o-dropdown--menu .dropdown-item div span:contains('My Belgian Company - TEST')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger:
                ".o_menu_systray .o_switch_company_menu button.dropdown-toggle span:contains('My Belgian Company - TEST')",
        },
        {
            content: "Recruitment",
            trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
            run: "click",
        },
        {
            content: "Jobs list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Create Job Position",
            trigger: "button.o_list_button_add",
            run: "click",
        },
        {
            content: "Job's Name",
            trigger: ".o_field_widget[name='name'] textarea",
            run: "edit Experienced Developer (BE)",
        },
        {
            content: "Select Recruitment Tab",
            trigger: ".o_notebook ul > li > a:contains(Recruitment)",
            run: "click",
        },
        {
            content: "Contract Template",
            trigger: ".o_field_widget.o_field_many2one[name=default_contract_id] input",
            run: `edit New Developer Template Contract`,
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains(New Developer Template Contract)",
            run: "click",
        },
        {
            content: "Save Job",
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
        {
            content: "Open Application Pipe",
            trigger: "button.oe_stat_button:contains(Applications)",
            run: "click",
        },
        {
            trigger: '.o_breadcrumb .active:contains("Applications")',
        },
        {
            content: "Create Applicant",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        // Test Applicant
        {
            content: "Applicant Name",
            trigger: 'div [name="candidate_id"] input',
            run: "edit Mitchell Admin 2",
        },
        {
            content: "Applicant Name",
            trigger: "a:contains('Mitchell Admin 2')",
            run: "click",
        },
        {
            content: "Applicant's Email",
            trigger: '.o_group [name="email_from"] input',
            run: "edit mitchell2.stephen@example.com",
        },
        {
            trigger: ".o_statusbar_buttons",
        },
        {
            content: "Generate Offer",
            trigger: ".o_statusbar_buttons > button:contains('Generate Offer')",
            run: "click",
        },
        {
            content: "Open compose email wizard",
            trigger: "button[name='action_send_by_email']",
            run: "click",
        },
        {
            trigger: ".modal-dialog .btn-primary:contains('Send')",
        },
        {
            content: "Send Offer",
            trigger: "button.o_mail_send",
            run: "click",
        },
        {
            trigger: "button[name='action_jump_to_offer']",
        },
        {
            content: "Unlog + Go on Configurator",
            trigger: ".o-mail-Chatter .o-mail-Message:eq(0) a",
            async run() {
                const offer_link = queryOne(".o-mail-Chatter .o-mail-Message:eq(0) a").href;
                // Retrieve the link without the origin to avoid
                // mismatch between localhost:8069 and 127.0.0.1:8069
                // when running the tour with chrome headless
                var regex = "/salary_package/simulation/.*";
                var url = offer_link.match(regex)[0];
                await fetch("/web/session/logout", { method: "GET" });
                    window.location.href = window.location.origin + url;
            },
            expectUnloadPage: true,
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Choose a car",
            trigger: "input[name=fold_company_car_total_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="2671.14"]',
        },
        {
            content: "Unchoose a car",
            trigger: "input[name=fold_company_car_total_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Choose Public Transportation",
            trigger: "input[name=fold_public_transport_reimbursed_amount]:not(:visible)",
            run: "click",
        },
        {
            content: "Set Public Transportation Amount",
            trigger: 'input[name="public_transport_reimbursed_amount_manual"]',
            run: "edit 100 && click label:contains(Transportation)",
        },
        {
            trigger: 'input[name="Gross"][value="2976.62"]',
        },
        {
            content: "Unchoose Public Transportation",
            trigger: "input[name=fold_public_transport_reimbursed_amount]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Choose Train Transportation",
            trigger: "input[name=fold_train_transport_reimbursed_amount]:not(:visible)",
            run: "click",
        },
        {
            content: "Set Train Transportation Amount",
            trigger: 'input[name="train_transport_reimbursed_amount_manual"]',
            run: "edit 150 && click label:contains(Transportation)",
        },
        {
            trigger: 'input[name="Gross"][value="2917.47"]',
        },
        {
            content: "Unchoose Public Transportation",
            trigger: "input[name=fold_train_transport_reimbursed_amount]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Choose Private Car Transportation",
            trigger: "input[name=fold_private_car_reimbursed_amount]:not(:visible)",
            run: "click",
        },
        {
            content: "Set Private Car Transportation Amount",
            trigger: 'input[name="private_car_reimbursed_amount_manual"]',
            run: "edit 150 && click label:contains(Transportation)",
        },
        {
            trigger: 'input[name="Gross"][value="2886.87"]',
        },
        {
            content: "Change km_home_work on personal info",
            trigger: 'input[name="km_home_work"]',
            run: "edit 75 && click label:contains(Transportation)",
        },
        {
            trigger: 'input[name="Gross"][value="2930.88"]',
        },
        {
            content: "Reset 150 km",
            trigger: 'input[name="km_home_work"]',
            run: "edit 150 && click label:contains(Transportation)",
        },
        {
            trigger: 'input[name="Gross"][value="2886.87"]',
        },
        {
            content: "Unchoose Private Car Transportation",
            trigger: "input[name=fold_private_car_reimbursed_amount]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Choose a Bike",
            trigger: "input[name=fold_company_bike_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="2982.81"]',
        },
        {
            content: "Choose Bike 2",
            trigger: "select[name=select_company_bike_depreciated_cost]:not(:visible)",
            run: "selectByLabel Bike 2",
        },
        {
            trigger: 'input[name="Gross"][value="2965.61"]',
        },
        {
            content: "Choose Bike 1",
            trigger: "select[name=select_company_bike_depreciated_cost]:not(:visible)",
            run: "selectByLabel Bike 1",
        },
        {
            trigger: 'input[name="Gross"][value="2982.81"]',
        },
        {
            content: "Unchoose Bike",
            trigger: "input[name=fold_company_bike_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Unset Internet",
            trigger: 'input[name="internet_manual"]',
            run: "edit 0 && click label:contains(Internet)",
        },
        {
            trigger: 'input[name="Gross"][value="3026.13"]',
        },
        {
            content: "Reset Internet",
            trigger: 'input[name="internet_manual"]',
            run: "edit 38 && click label:contains(Internet)",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Unset Mobile",
            trigger: "input[name=mobile_radio]:eq(0):not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3020.63"]',
        },
        {
            content: "Reset Mobile",
            trigger: "input[name=mobile_radio]:eq(1):not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Take Extra-Legal Leaves",
            trigger: 'input[list="holidays_range"]',
            run: "range 10",
        },
        {
            trigger: 'input[name="Gross"][value="2860.17"]',
        },
        {
            content: "Untake Extra-Legal Leaves",
            trigger: 'input[list="holidays_range"]',
            run: "range 0",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Take IP",
            trigger: "input[name=ip_value_radio]:eq(1):not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2404.33"]',
        },
        {
            content: "Untake IP",
            trigger: "input[name=ip_value_radio]:eq(0):not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Untake Rep Fees",
            trigger: "input[name=representation_fees_radio]:eq(0):not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3103.16"]',
        },
        {
            content: "Retake Rep Fees",
            trigger: "input[name=representation_fees_radio]:eq(1):not(:visible)",
            run: "click",
        },
        // In order to choose Fuel card, the mandatory advantage, company car, should be selected first
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Choose a car",
            trigger: "input[name=fold_company_car_total_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="2671.14"]',
        },
        {
            content: "Take Fuel Card",
            trigger: 'input[list="fuel_card_range"]',
            run: "range 250",
        },
        {
            trigger: 'input[name="Gross"][value="2499.2"]',
        },
        {
            content: "Untake Fuel Card",
            trigger: 'input[list="fuel_card_range"]',
            run: "range 0",
        },
        {
            trigger: 'input[name="Gross"][value="2671.14"]',
        },
        {
            content: "Unchoose a car",
            trigger: "input[name=fold_company_car_total_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            content: "Name",
            trigger: 'input[name="name"]',
            run: "edit Nathalie",
        },
        {
            content: "BirthDate",
            trigger: '[name="birthday"] input',
            run: function () {
                this.anchor.value = "2017-09-01";
            },
        },
        {
            content: "Gender",
            trigger: '[name="gender"] input[value="female"]:not(:visible)',
            run: "check",
        },
        {
            content: "National Identification Number",
            trigger: 'input[name="identification_id"]',
            run: "edit 11.11.11-111.11",
        },
        {
            content: "Street",
            trigger: 'input[name="private_street"]',
            run: "edit Rue des Wallons",
        },
        {
            content: "City",
            trigger: 'input[name="private_city"]',
            run: "edit Louvain-la-Neuve",
        },
        {
            content: "Zip Code",
            trigger: 'input[name="private_zip"]',
            run: "edit 1348",
        },
        {
            content: "Email",
            trigger: 'input[name="private_email"]',
            run: "edit nathalie.stephen@example.com",
        },
        {
            content: "Phone Number",
            trigger: 'input[name="private_phone"]',
            run: "edit 1234567890",
        },
        {
            content: "Place of Birth",
            trigger: 'input[name="place_of_birth"]',
            run: "edit Brussels",
        },
        {
            content: "KM Home/Work",
            trigger: 'input[name="km_home_work"]',
            run: "edit 75",
        },
        {
            content: "Certificate",
            trigger: "select[name=certificate]:not(:visible)",
            run: "selectByLabel Master",
        },
        {
            content: "School",
            trigger: 'input[name="study_school"]',
            run: "edit UCL",
        },
        {
            content: "School Level",
            trigger: 'input[name="study_field"]',
            run: "edit Civil Engineering, Applied Mathematics",
        },
        {
            content: "Set Seniority at Hiring",
            trigger: 'input[name="l10n_be_scale_seniority"]',
            run: "edit 1",
        },
        {
            content: "Bank Account",
            trigger: 'input[name="acc_number"]',
            run: "edit BE10 3631 0709 4104",
        },
        {
            content: "Private License Plate",
            trigger: 'input[name="private_car_plate"]',
            run: "edit 1-ABC-123",
        },
        {
            content: "Emergency Contact",
            trigger: 'input[name="emergency_contact"]',
            run: "edit Batman",
        },
        {
            content: "Emergency Phone",
            trigger: 'input[name="emergency_phone"]',
            run: "edit +32 2 290 34 90",
        },
        {
            content: "Nationality",
            trigger: "select[name=country_id]:not(:visible)",
            run: "selectByLabel Belgium",
        },
        {
            content: "Country of Birth",
            trigger: "select[name=country_of_birth]:not(:visible)",
            run: "selectByLabel Belgium",
        },
        {
            content: "Lang",
            trigger: "select[name=lang]:not(:visible)",
            run: "selectByLabel English",
        },
        {
            content: "Check Disabled",
            trigger: "input[name=disabled]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Uncheck Disabled",
            trigger: "input[name=disabled]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Set Married",
            trigger: "select[name=marital]:not(:visible)",
            run: "selectByLabel Married",
        },
        {
            trigger: 'input[name="Net"][value="2430.31"]',
        },
        {
            content: "Check Disabled Spouse Bool",
            trigger: "input[name=disabled_spouse_bool]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2430.31"]',
        },
        {
            content: "Uncheck Disabled Spouse Bool",
            trigger: "input[name=disabled_spouse_bool]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2430.31"]',
        },
        {
            content: "Set High Spouse Income",
            trigger: "select[name=spouse_fiscal_status]:not(:visible)",
            run: "selectByLabel With High Income",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Unset Married",
            trigger: "select[name=marital]:not(:visible)",
            run: "selectByLabel Single",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Set Children",
            trigger: "input[name=children]",
            run: "edit 3 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2443.9"]',
        },
        {
            content: "Check Disabled Children",
            trigger: "input[name=disabled_children_bool]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2443.9"]',
        },
        {
            content: "Set 1 Disabled Children",
            trigger: "input[name=disabled_children_number]",
            run: "edit 1 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2662.9"]',
        },
        {
            content: "Set 0 Disabled Children",
            trigger: "input[name=disabled_children_number]",
            run: "edit 0 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2443.9"]',
        },
        {
            content: "Uncheck Disabled Children",
            trigger: "input[name=disabled_children_bool]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2443.9"]',
        },
        {
            content: "Unset Children",
            trigger: "input[name=children]",
            run: "edit 0 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Check Other Dependent People",
            trigger: "input[name=other_dependent_people]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Set 2 Senior",
            trigger: "input[name=other_senior_dependent]",
            run: "edit 2 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2281.9"]',
        },
        {
            content: "Set 1 disabled Senior",
            trigger: "input[name=other_disabled_senior_dependent]",
            run: "edit 1 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2365.9"]',
        },
        {
            content: "Set 2 Juniors",
            trigger: "input[name=other_juniors_dependent]",
            run: "edit 2 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2443.9"]',
        },
        {
            content: "Set 1 disabled Junior",
            trigger: "input[name=other_disabled_juniors_dependent]",
            run: "edit 1 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2482.9"]',
        },
        {
            content: "Unset 1 disabled Senior over 2",
            trigger: "input[name=other_disabled_juniors_dependent]",
            run: "edit 0 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2443.9"]',
        },
        {
            content: "Unset 2 Juniors",
            trigger: "input[name=other_juniors_dependent]",
            run: "edit 0 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2365.9"]',
        },
        {
            content: "Unset 1 disabled Senior",
            trigger: "input[name=other_disabled_senior_dependent]",
            run: "edit 0 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2281.9"]',
        },
        {
            content: "Unset 2 Seniors",
            trigger: "input[name=other_senior_dependent]",
            run: "edit 0 && click h2:contains(Situation)",
        },
        {
            trigger: 'input[name="Net"][value="2113.9"]',
        },
        {
            content: "Uncheck Other Dependent People",
            trigger: "input[name=other_dependent_people]:not(:visible)",
            run: "click",
        },
        {
            trigger: 'input[name="Gross"][value="3000"]',
        },
        {
            content: "Choose a car",
            trigger: "input[name=fold_company_car_total_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            content: "Choose a new car",
            trigger: `select[name="select_company_car_total_depreciated_cost"]:not(:visible)`,
            run: "selectByLabel a3",
        },
        // set personal info
        {
            content: "Upload ID card copy (Both Sides)",
            trigger: 'input[name="id_card"]',
            async run() {
                const file = new File(["hello, world"], "employee_id_card.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="id_card"]', [file]);
            },
        },
        {
            content: "Upload Mobile Subscription Invoice",
            trigger: 'input[name="mobile_invoice"]',
            async run() {
                const file = new File(["hello, world"], "employee_mobile_invoice.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="mobile_invoice"]', [file]);
            },
        },
        {
            content: "Upload Sim Card Copy",
            trigger: 'input[name="sim_card"]',
            async run() {
                const file = new File(["hello, world"], "employee_sim_card.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="sim_card"]', [file]);
            },
        },
        {
            content: "Upload Internet Subscription invoice",
            trigger: 'input[name="internet_invoice"]',
            async run() {
                const file = new File(["hello, world"], "employee_internet_invoice.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="internet_invoice"]', [file]);
            },
        },
        {
            content: "Upload Driving License",
            trigger: 'input[name="driving_license"]',
            async run() {
                const file = new File(["hello, world"], "employee_driving_license.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="driving_license"]', [file]);
            },
        },
        {
            trigger: 'input[name="Gross"][value="2671.14"]',
        },
        {

            content: "Take Extra-Legal Leaves",
            trigger: 'input[list="holidays_range"]',
            run: function () {
                $('input[list="holidays_range"]').val(3);
                $('input[list="holidays_range"]').trigger('change');
            },
        },
        {
            trigger: 'input[name="Gross"][value="2629.19"]',
        },
        {
            content: "submit",
            trigger: "button#hr_cs_submit",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Next 1",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Type Date",
            trigger: ":iframe input.ui-selected",
            run: "edit 17/09/2018",
        },
        // fill signature
        {
            content: "Next 3",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Click Signature",
            trigger: ":iframe button.o_sign_sign_item",
            run: "click",
        },
        {
            content: "Click Auto",
            trigger: "a.o_web_sign_auto_button:contains('Auto')",
            run: "click",
        },
        {
            content: "Adopt & Sign",
            trigger: "footer.modal-footer button.btn-primary:enabled",
            run: "click",
        },
        {
            content: "Wait modal closed",
            trigger: ":iframe body:not(:has(footer.modal-footer button.btn-primary))",
        },
        // fill date
        {
            content: "Next 4",
            trigger: ':iframe .o_sign_sign_item_navigator:contains("next")',
            run: "click",
        },
        {
            content: "Type Date",
            trigger: ":iframe input.ui-selected",
            run: "edit 17/09/2018",
        },
        {
            content: "Validate and Sign",
            trigger: ".o_sign_validate_banner button",
            run: "click",
        },
    ],
});
registry.category("web_tour.tours").add("hr_contract_salary_tour_hr_sign", {
    url: "/odoo",
    wait_for: Promise.resolve(odoo.__TipTemplateDef),
    steps: () => [
        {
            content: "Log into Belgian Company",
            trigger: ".o_menu_systray .o_switch_company_menu button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Log into Belgian Company",
            trigger:
                ".o-dropdown--menu .dropdown-item div span:contains('My Belgian Company - TEST')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger:
                ".o_menu_systray .o_switch_company_menu button.dropdown-toggle span:contains('My Belgian Company - TEST')",
        },
        {
            content: "Recruitment",
            trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
            run: "click",
        },
        {
            content: "Jobs list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Select Our Job",
            trigger: 'table.o_list_table tbody td:contains("Experienced Developer")',
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
        {
            content: "Open Application Pipe",
            trigger: "button.oe_stat_button:contains(Applications)",
            run: "click",
        },
        {
            content: "Select Our Applicant",
            trigger: 'div.o_kanban_view span.fw-bold:contains("Mitchell Admin 2")',
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
        {
            content: "Open Contracts",
            trigger: "button.oe_stat_button:contains(Contracts)",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
        {
            content: "Open Signature Request",
            trigger: "button.oe_stat_button:contains(Sign)",
            run: "click",
        },
        {
            trigger: "iframe.o_sign_pdf_iframe",
        },
        {
            content: "Sign",
            trigger: "button:contains(Sign Now)",
            run: "click",
        },
        {
            trigger: "iframe.o_sign_pdf_iframe",
        },
        {
            content: "Next 5",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Click Signature",
            trigger: ":iframe button.o_sign_sign_item",
            run: "click",
        },
        {
            content: "Validate and Sign",
            trigger: ".o_sign_validate_banner button",
            run: "click",
        },
    ],
});
registry.category("web_tour.tours").add("hr_contract_salary_tour_2", {
    url: "/odoo",
    wait_for: Promise.resolve(odoo.__TipTemplateDef),
    steps: () => [
        {
            content: "Log into Belgian Company",
            trigger: ".o_menu_systray .o_switch_company_menu button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Log into Belgian Company",
            trigger:
                ".o-dropdown--menu .dropdown-item div span:contains('My Belgian Company - TEST')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger:
                ".o_menu_systray .o_switch_company_menu button.dropdown-toggle span:contains('My Belgian Company - TEST')",
        },
        {
            content: "Recruitment",
            trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
            run: "click",
        },
        {
            content: "Jobs list view",
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Select Our Job",
            trigger: 'table.o_list_table tbody td:contains("Experienced Developer")',
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
        {
            content: "Open Application Pipe",
            trigger: "button.oe_stat_button:contains(Applications)",
            run: "click",
        },
        {
            trigger: '.o_breadcrumb .active:contains("Applications")',
        },
        {
            content: "Create Applicant",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Applicant Name",
            trigger: 'div [name="candidate_id"] input',
            run: "edit Mitchell Admin 3",
        },
        {
            content: "Applicant Name",
            trigger: "a:contains('Mitchell Admin 3')",
            run: "click",
        },
        {
            content: "Add Email Address",
            trigger: '.o_group [name="email_from"] input',
            run: "edit mitchell2.stephen@example.com",
        },
        {
            content: "Confirm Applicant Creation",
            trigger: ".o_control_panel button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_statusbar_status button.dropdown-toggle:enabled",
            content: "Move applicant to hired stage",
            run: "click",
        },
        {
            content: "Recruitment",
            trigger: '.dropdown-item:contains("Contract Signed")',
            run: "click",
        },
        {
            trigger: ".o_statusbar_buttons",
        },
        {
            content: "Create Employee",
            trigger: ".o_statusbar_buttons > button[name='create_employee_from_applicant']",
            run: "click",
        },
        {
            content: "Add Manager",
            trigger: ".nav-link:contains('Work Information')",
            run: "click",
        },
        {
            content: "Manager",
            trigger:
                ".o_field_widget.o_field_many2one_avatar_user.o_field_many2one_avatar[name=parent_id] input",
            run: `edit Mitchell`,
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains(Mitchell)",
            run: "click",
        },
        {
            content: "Add Work Email",
            trigger: '.o_group [name="work_email"] input',
            run: "edit mitchel3_work@example.com",
        },
        {
            trigger: '.o-mail-Message-body a[href*="/action-hr.plan_wizard_action"]',
        },
        {
            content: "Save Employee",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
        {
            content: "Create Contract",
            trigger: '.o-form-buttonbox .oe_stat_button:contains("Contracts")',
            run: "click",
        },
        {
            content: "Salary Structure Type",
            trigger: ".o_field_widget.o_field_many2one[name=structure_type_id] input",
            run: `edit CP200: Belgian Employee`,
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains('CP200: Belgian Employee')",
            run: "click",
        },
        {
            content: "Contract Reference",
            trigger: '.o_field_widget.o_field_char[name="name"] input',
            run: "edit Mitchell Admin PFI Contract",
        },
        {
            content: "Select Contract Details Tab",
            trigger: ".o_notebook ul > li > a:contains(Details)",
            run: "click",
        },
        {
            content: "HR Responsible",
            trigger:
                "div.o_field_widget.o_required_modifier.o_field_many2one_avatar_user.o_field_many2one_avatar[name=hr_responsible_id] input",
            run: `edit Mitchell`,
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains('Mitchell Admin')",
            run: "click",
        },
        {
            content: "Select Signatories Tab",
            trigger: ".o_notebook ul > li > a:contains(Signatories)",
            run: "click",
        },
        {
            content: "Contract Update Template",
            trigger: ".o_field_widget.o_field_many2one[name=contract_update_template_id] input",
            run: `edit test_employee_contract`,
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains('test_employee_contract')",
            run: "click",
        },
        {
            content: "New Contract Document Template",
            trigger: ".o_field_widget.o_field_many2one[name=sign_template_id] input",
            run: `edit test_employee_contract`,
        },
        {
            content: "Select Contract Details Tab",
            trigger: ".o_notebook ul > li > a:contains(Details)",
            run: "click",
        },
        {
            content: "Select Salary Information Tab",
            trigger: ".o_notebook ul > li > a:contains(Salary)",
            run: "click",
        },
        {
            content: "Contract Information",
            trigger: "div[name='wage'] input",
            run: "edit 2950",
        },
        {
            content: "Contract Information",
            trigger: "div.o_field_boolean[name='transport_mode_car'] input",
            run: "click",
        },
        {
            content: "Contract Information",
            trigger: ".o_field_widget.o_field_many2one[name=car_id] input",
            run: `edit JFC`,
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains('1-JFC-095')",
            run: "click",
        },
        {
            content: "Contract Information",
            trigger: "div[name='fuel_card'] input",
            run: "edit 250 && click h2:contains(Monthly)",
        },
        {
            content: "Contract Information",
            trigger: "div[name='commission_on_target'] input",
            run: "edit 1000 && click h2:contains(Monthly)",
        },
        {
            content: "Contract Information",
            trigger: "[name='ip_wage_rate'] input",
            run: "edit 25 && click h2:contains(Monthly)",
        },
        {
            content: "Contract Information",
            trigger: "div.o_field_boolean[name='ip'] input",
            run: "click",
        },
        {
            content: "Save Contract",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Go back on the employee",
            trigger: "li > a:contains('Mitchell Admin 3'):last",
            run: "click",
        },
        {
            content: "Go on Contract",
            trigger: '.o-form-buttonbox .oe_stat_button:contains("In Contract Since")',
            run: "click",
        },
        {
            trigger: ".o_statusbar_buttons",
        },
        {
            content: "Generate Offer",
            trigger: ".o_statusbar_buttons > button:contains('Generate Offer')",
            run: "click",
        },
        {
            content: "Select Contract",
            trigger: ".o_field_widget.o_field_many2one[name=contract_template_id] input",
            run: `edit Mitchell Admin PFI`,
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains('Mitchell Admin PFI Contract')",
            run: "click",
        },
        {
            content: "Enable wishlist",
            trigger: ".o_field_widget.o_field_boolean[name='new_car'] input",
            run: function () {
                if (this.anchor.value == "false"){
                    this.anchor.value = "true";
                }    
            },
        },
        {
            content: "Open compose email wizard",
            trigger: "button[name='action_send_by_email']",
            run: "click",
        },
        {
            content: "Send Offer",
            trigger: "button.o_mail_send",
            run: "click",
        },
        {
            trigger: "button[name='action_jump_to_offer']",
        },
        {
            content: "Go on configurator",
            trigger: ".o-mail-Chatter .o-mail-Message:eq(0) a",
            run: function () {
                const offer_link = queryOne(".o-mail-Chatter .o-mail-Message:eq(0) a").href;
                // Retrieve the link without the origin to avoid
                // mismatch between localhost:8069 and 127.0.0.1:8069
                // when running the tour with chrome headless
                var regex = "/salary_package/simulation/.*";
                var url = offer_link.match(regex)[0];
                window.location.href = window.location.origin + url;
            },
            expectUnloadPage: true,
        },
        {
            content: "Unchoose default car",
            trigger: "input[name=fold_company_car_total_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            content: "Choose to be in waiting list for car",
            trigger: "input[name=fold_wishlist_car_total_depreciated_cost]:not(:visible)",
            run: "click",
        },
        {
            trigger: "label[for=wishlist_car_total_depreciated_cost]",
        },
        {
            content: "Choose a new car in waiting list",
            trigger: `select[name="select_wishlist_car_total_depreciated_cost"]:not(:visible)`,
            run: "selectByLabel Corsa",
        },
        {
            content: "BirthDate",
            trigger: 'input[name="birthday"]',
            run() {
                this.anchor.value = "2017-09-01";
            },
        },
        {
            content: "Gender",
            trigger: "input[name=gender]:not(:visible)",
            run: function () {
                document.querySelector('input[value="female"]').checked = true;
            },
        },
        {
            content: "National Identification Number",
            trigger: 'input[name="identification_id"]',
            run: "edit 11.11.11-111.11",
        },
        {
            content: "Street",
            trigger: 'input[name="private_street"]',
            run: "edit Rue des Wallons",
        },
        {
            content: "City",
            trigger: 'input[name="private_city"]',
            run: "edit Louvain-la-Neuve",
        },
        {
            content: "Zip Code",
            trigger: 'input[name="private_zip"]',
            run: "edit 1348",
        },
        {
            content: "Email",
            trigger: 'input[name="private_email"]',
            run: "edit mitchell2.stephen@example.com",
        },
        {
            content: "Phone Number",
            trigger: 'input[name="private_phone"]',
            run: "edit 1234567890",
        },
        {
            content: "Place of Birth",
            trigger: 'input[name="place_of_birth"]',
            run: "edit Brussels",
        },
        {
            content: "KM Home/Work",
            trigger: 'input[name="km_home_work"]',
            run: "edit 75",
        },
        {
            trigger: "label[for=certificate]",
        },
        {
            content: "Certificate",
            trigger: "select[name=certificate]:not(:visible)",
            run: "selectByLabel Master",
        },
        {
            content: "School",
            trigger: 'input[name="study_school"]',
            run: "edit UCL",
        },
        {
            content: "School Level",
            trigger: 'input[name="study_field"]',
            run: "edit Civil Engineering, Applied Mathematics",
        },
        {
            content: "Set Seniority at Hiring",
            trigger: 'input[name="l10n_be_scale_seniority"]',
            run: "edit 1 && click body",
        },
        {
            trigger: "label[for=lang]:eq(0)",
        },
        {
            content: "Lang",
            trigger: "select[name=lang]:not(:visible)",
            run: "selectByLabel English",
        },
        {
            content: "Bank Account",
            trigger: 'input[name="acc_number"]',
            run: "edit BE10 3631 0709 4104",
        },
        {
            content: "Bank Account",
            trigger: 'input[name="emergency_contact"]',
            run: "edit Batman",
        },
        {
            content: "Bank Account",
            trigger: 'input[name="emergency_phone"]',
            run: "edit +32 2 290 34 90",
        },
        {
            trigger: "label[for=country_id]:eq(0)",
        },
        {
            content: "Nationality",
            trigger: "select[name=country_id]:not(:visible)",
            run: "selectByLabel Belgium",
        },
        {
            content: "Country of Birth",
            trigger: "select[name=country_of_birth]:not(:visible)",
            run: "selectByLabel Belgium",
        },
        {
            trigger: "label[for=private_country_id]:eq(0)",
        },
        {
            content: "Country",
            trigger: "select[name=private_country_id]:not(:visible)",
            run: "selectByLabel Belgium",
        },
        {
            content: "Set 0 Children",
            trigger: "input[name=children]",
            run: "edit 0 && click body",
        },
        // set personal info
        {
            content: "Upload ID card copy (Both Sides)",
            trigger: 'input[name="id_card"]',
            async run() {
                const file = new File(["hello, world"], "employee_id_card.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="id_card"]', [file]);
            },
        },
        {
            content: "Upload Mobile Subscription Invoice",
            trigger: 'input[name="mobile_invoice"]',
            async run() {
                const file = new File(["hello, world"], "employee_mobile_invoice.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="mobile_invoice"]', [file]);
            },
        },
        {
            content: "Upload Sim Card Copy",
            trigger: 'input[name="sim_card"]',
            async run() {
                const file = new File(["hello, world"], "employee_sim_card.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="sim_card"]', [file]);
            },
        },
        {
            content: "Upload Internet Subscription invoice",
            trigger: 'input[name="internet_invoice"]',
            async run() {
                const file = new File(["hello, world"], "employee_internet_invoice.pdf", {
                    type: "application/pdf",
                });
                await inputFiles('input[name="internet_invoice"]', [file]);
            },
        },
        {
            content: "submit",
            trigger: "button#hr_cs_submit",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "Next 6",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Type Date",
            trigger: ":iframe input.ui-selected",
            run: "edit 17/09/2018",
        },
        // fill signature
        {
            content: "Next 8",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Click Signature",
            trigger: ":iframe button.o_sign_sign_item",
            run: "click",
        },
        {
            content: "Click Auto",
            trigger: "a.o_web_sign_auto_button:contains('Auto')",
            run: "click",
        },
        {
            content: "Adopt & Sign",
            trigger: "footer.modal-footer button.btn-primary:enabled",
            run: "click",
        },
        {
            content: "Wait modal closed",
            trigger: ":iframe body:not(:has(footer.modal-footer button.btn-primary))",
        },
        // fill date
        {
            content: "Next 9",
            trigger: ':iframe .o_sign_sign_item_navigator:contains("next")',
            run: "click",
        },
        {
            content: "Type Date",
            trigger: ":iframe input.ui-selected",
            run: "edit 17/09/2018",
        },
        {
            content: "Validate and Sign",
            trigger: ".o_sign_validate_banner button",
            run: "click",
        },
        {
            content: "Go on configurator",
            trigger: "h1.hr_cs_brand_optional",
            run: function () {
                redirect("/odoo");
            },
            expectUnloadPage: true,
        },
        {
            content: "Check home page is loaded",
            trigger: "a.o_app.o_menuitem",
        },
    ],
});

registry.category("web_tour.tours").add("hr_contract_salary_tour_counter_sign", {
    url: "/odoo",
    wait_for: Promise.resolve(odoo.__TipTemplateDef),
    steps: () => [
        {
            content: "Log into Belgian Company",
            trigger: ".o_menu_systray .o_switch_company_menu button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Log into Belgian Company",
            trigger:
                ".o-dropdown--menu .dropdown-item div span:contains('My Belgian Company - TEST')",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: `.oe_topbar_name:contains(My Belgian Company - TEST)`,
        },
        {
            content: "Open Activity Systray",
            trigger: ".o-mail-ActivityMenu-counter",
            run: "click",
        },
        {
            content: "Open Sign Requests",
            trigger: '.o-dropdown--menu .list-group-item:contains("Signature")',
            run: "click",
        },
        {
            content: "Go to Signable Document",
            trigger: "button[name='go_to_signable_document']",
            run: "click",
        },
        {
            content: "Next 1",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Next 2",
            trigger: ":iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Click Signature",
            trigger: ":iframe button.o_sign_sign_item",
            run: "click",
        },
        {
            content: "Click Auto",
            trigger: "a.o_web_sign_auto_button:contains('Auto')",
            run: "click",
        },
        {
            content: "Adopt & Sign",
            trigger: "footer.modal-footer button.btn-primary:enabled",
            run: "click",
        },
        {
            trigger: ":iframe body:not(:has(footer.modal-footer button.btn-primary))",
        },
        {
            content: "Validate and Sign",
            trigger: ".o_sign_validate_banner button",
            run: "click",
        },
    ],
});
