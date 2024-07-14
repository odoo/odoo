/* @odoo-module */

import { registry } from "@web/core/registry";
import { createFile, inputFiles } from "@web/../tests/utils";

registry.category("web_tour.tours").add("hr_contract_salary_tour", {
    test: true,
    url: "/my",
    wait_for: Promise.resolve(odoo.__TipTemplateDef),
    steps: () => [
        {
            content: "Go on configurator",
            trigger: ".navbar",
            run: function () {
                window.location.href = window.location.origin + "/web";
            },
        },
        {
            content: "Log into Belgian Company",
            trigger: ".o_menu_systray .o_switch_company_menu button.dropdown-toggle",
            run: "click",
        },
        {
            content: "Log into Belgian Company",
            trigger:
                ".o_menu_systray .o_switch_company_menu .dropdown-item div span:contains('My Belgian Company - TEST')",
            run: "click",
        },
        {
            content: "Recruitment",
            trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
            extra_trigger:
                ".o_menu_systray .o_switch_company_menu button.dropdown-toggle span:contains('My Belgian Company - TEST')",
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
            run: "text Experienced Developer (BE)",
        },
        {
            content: "Select Recruitment Tab",
            trigger: ".o_notebook ul > li > a:contains(Recruitment)",
            run: "click",
        },
        {
            content: "Contract Template",
            trigger: ".o_field_widget.o_field_many2one[name=default_contract_id]",
            run: function (actions) {
                actions.text("New Developer Template Contract", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains(New Developer Template Contract)",
            auto: true,
        },
        {
            content: "Save Job",
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            content: "Open Application Pipe",
            trigger: "button.oe_stat_button:contains(Applications)",
            extra_trigger: ".o_form_saved",
            run: "click",
        },
        {
            content: "Create Applicant",
            trigger: ".o-kanban-button-new",
            extra_trigger: '.o_breadcrumb .active:contains("Applications")',
            run: "click",
        },
        // Test Applicant
        {
            content: "Applicant Name",
            trigger: '.oe_title [name="name"] textarea',
            run: "text Jojo Zeboss' Application",
        },
        {
            content: "Applicant's Name",
            trigger: '.oe_title [name="partner_name"] input',
            run: "text Mitchell Admin 2",
        },
        {
            content: "Applicant's Email",
            trigger: '.o_group [name="email_from"] input',
            run: "text mitchell2.stephen@example.com",
        },
        {
            content: "Generate Offer",
            trigger: ".o_statusbar_buttons > button:contains('Generate Offer')",
            extra_trigger: ".o_statusbar_buttons",
            run: "click",
        },
        {
            content: "Send Offer",
            trigger: "button[name='action_send_offer']",
            extra_trigger: ".modal-dialog .btn-primary:contains('Save')",
            run: "click",
        },
        {
            content: "Send Offer",
            trigger: "button[name='action_send_mail']",
            extra_trigger: ".modal-dialog .btn-primary:contains('Send')",
            run: "click",
        },
        {
            content: "Click on Offers Stat Button",
            trigger: "button[name='action_show_offers']",
            run: "click",
        },
        {
            content: "Unlog + Go on Configurator",
            trigger: ".o-mail-Chatter .o-mail-Message:eq(0) a",
            run: function () {
                var simulation_link = $(".o-mail-Chatter .o-mail-Message:eq(0) a")[0].href;
                // Retrieve the link without the origin to avoid
                // mismatch between localhost:8069 and 127.0.0.1:8069
                // when running the tour with chrome headless
                var regex = "/salary_package/simulation/.*";
                var url = simulation_link.match(regex)[0];
                $.get("/web/session/logout", function () {
                    window.location.href = window.location.origin + url;
                });
            },
            extra_trigger: "button[name='action_jump_to_offer']",
        },
        {
            content: "Choose a car",
            trigger: 'input[name="fold_company_car_total_depreciated_cost"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Unchoose a car",
            trigger: 'input[name="fold_company_car_total_depreciated_cost"]',
            extra_trigger: 'input[name="Gross"][value="2671.14"]',
            run: "click",
        },
        {
            content: "Choose Public Transportation",
            trigger: 'input[name="fold_public_transport_reimbursed_amount"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Set Public Transportation Amount",
            trigger: 'input[name="public_transport_reimbursed_amount_manual"]',
            run: "text 100",
        },
        {
            content: "Unchoose Public Transportation",
            trigger: 'input[name="fold_public_transport_reimbursed_amount"]',
            extra_trigger: 'input[name="Gross"][value="2976.62"]',
            run: "click",
        },
        {
            content: "Choose Train Transportation",
            trigger: 'input[name="fold_train_transport_reimbursed_amount"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Set Train Transportation Amount",
            trigger: 'input[name="train_transport_reimbursed_amount_manual"]',
            run: "text 150",
        },
        {
            content: "Unchoose Public Transportation",
            trigger: 'input[name="fold_train_transport_reimbursed_amount"]',
            extra_trigger: 'input[name="Gross"][value="2917.47"]',
            run: "click",
        },
        {
            content: "Choose Private Car Transportation",
            trigger: 'input[name="fold_private_car_reimbursed_amount"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Set Private Car Transportation Amount",
            trigger: 'input[name="private_car_reimbursed_amount_manual"]',
            run: "text 150",
        },
        {
            content: "Change km_home_work on personal info",
            trigger: 'input[name="km_home_work"]',
            extra_trigger: 'input[name="Gross"][value="2886.87"]',
            run: "text 75",
        },
        {
            content: "Reset 150 km",
            trigger: 'input[name="km_home_work"]',
            extra_trigger: 'input[name="Gross"][value="2930.88"]',
            run: "text 150",
        },
        {
            content: "Unchoose Private Car Transportation",
            trigger: 'input[name="fold_private_car_reimbursed_amount"]',
            extra_trigger: 'input[name="Gross"][value="2886.87"]',
            run: "click",
        },
        {
            content: "Choose a Bike",
            trigger: 'input[name="fold_company_bike_depreciated_cost"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Choose Bike 2",
            trigger: "label[for=company_bike_depreciated_cost]",
            extra_trigger: 'input[name="Gross"][value="2982.81"]',
            run: function () {
                $("select[name=select_company_bike_depreciated_cost] option:contains(Bike 2)").prop(
                    "selected",
                    true
                );
                $("select[name=select_company_bike_depreciated_cost]").trigger("change");
            },
        },
        {
            content: "Choose Bike 1",
            trigger: "label[for=company_bike_depreciated_cost]",
            extra_trigger: 'input[name="Gross"][value="2965.61"]',
            run: function () {
                $("select[name=select_company_bike_depreciated_cost] option:contains(Bike 1)").prop(
                    "selected",
                    true
                );
                $("select[name=select_company_bike_depreciated_cost]").trigger("change");
            },
        },
        {
            content: "Unchoose Bike",
            trigger: 'input[name="fold_company_bike_depreciated_cost"]',
            extra_trigger: 'input[name="Gross"][value="2982.81"]',
            run: "click",
        },
        {
            content: "Unset Internet",
            trigger: 'input[name="internet_manual"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "text 0",
        },
        {
            content: "Reset Internet",
            trigger: 'input[name="internet_manual"]',
            extra_trigger: 'input[name="Gross"][value="3026.13"]',
            run: "text 38",
        },
        {
            content: "Unset Mobile",
            trigger: 'input[name="mobile_radio"]:eq(0)',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Reset Mobile",
            trigger: 'input[name="mobile_radio"]:eq(1)',
            extra_trigger: 'input[name="Gross"][value="3020.63"]',
            run: "click",
        },
        {
            content: "Take Extra-Legal Leaves",
            trigger: 'input[list="holidays_range"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: function () {
                $('input[list="holidays_range"]').val(10);
                $('input[list="holidays_range"]').trigger("change");
            },
        },
        {
            content: "Untake Extra-Legal Leaves",
            trigger: 'input[list="holidays_range"]',
            extra_trigger: 'input[name="Gross"][value="2860.17"]',
            run: function () {
                $('input[list="holidays_range"]').val(0);
                $('input[list="holidays_range"]').trigger("change");
            },
        },
        {
            content: "Take IP",
            trigger: 'input[name="ip_value_radio"]:eq(1)',
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: "click",
        },
        {
            content: "Untake IP",
            trigger: 'input[name="ip_value_radio"]:eq(0)',
            extra_trigger: 'input[name="Net"][value="2405.12"]',
            run: "click",
        },
        {
            content: "Untake Rep Fees",
            trigger: 'input[name="representation_fees_radio"]:eq(0)',
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: "click",
        },
        {
            content: "Retake Rep Fees",
            trigger: 'input[name="representation_fees_radio"]:eq(1)',
            extra_trigger: 'input[name="Gross"][value="3103.16"]',
            run: "click",
        },
        // In order to choose Fuel card, the mandatory advantage, company car, should be selected first
        {
            content: "Choose a car",
            trigger: 'input[name="fold_company_car_total_depreciated_cost"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Take Fuel Card",
            trigger: 'input[list="fuel_card_range"]',
            extra_trigger: 'input[name="Gross"][value="2671.14"]',
            run: function () {
                $('input[list="fuel_card_range"]').val(250);
                $('input[list="fuel_card_range"]').trigger("change");
            },
        },
        {
            content: "Untake Fuel Card",
            trigger: 'input[list="fuel_card_range"]',
            extra_trigger: 'input[name="Gross"][value="2499.2"]',
            run: function () {
                $('input[list="fuel_card_range"]').val(0);
                $('input[list="fuel_card_range"]').trigger("change");
            },
        },
        {
            content: "Unchoose a car",
            trigger: 'input[name="fold_company_car_total_depreciated_cost"]',
            extra_trigger: 'input[name="Gross"][value="2671.14"]',
            run: "click",
        },
        {
            content: "Name",
            trigger: 'input[name="name"]',
            run: "text Nathalie",
        },
        {
            content: "BirthDate",
            trigger: '[name="birthday"] input',
            run: function () {
                $("input[name='birthday']").val("2017-09-01");
            },
        },
        {
            content: "Gender",
            trigger: '[name="gender"] input',
            run: function () {
                $('input[value="female"]').prop("checked", true);
            },
        },
        {
            content: "National Identification Number",
            trigger: 'input[name="identification_id"]',
            run: "text 11.11.11-111.11",
        },
        {
            content: "Street",
            trigger: 'input[name="private_street"]',
            run: "text Rue des Wallons",
        },
        {
            content: "City",
            trigger: 'input[name="private_city"]',
            run: "text Louvain-la-Neuve",
        },
        {
            content: "Zip Code",
            trigger: 'input[name="private_zip"]',
            run: "text 1348",
        },
        {
            content: "Email",
            trigger: 'input[name="private_email"]',
            run: "text nathalie.stephen@example.com",
        },
        {
            content: "Phone Number",
            trigger: 'input[name="private_phone"]',
            run: "text 1234567890",
        },
        {
            content: "Place of Birth",
            trigger: 'input[name="place_of_birth"]',
            run: "text Brussels",
        },
        {
            content: "KM Home/Work",
            trigger: 'input[name="km_home_work"]',
            run: "text 75",
        },
        {
            content: "Certificate",
            trigger: "label[for=certificate]",
            run: function () {
                $("select[name=certificate] option:contains(Master)").prop("selected", true);
                $("select[name=certificate]").trigger("change");
            },
        },
        {
            content: "School",
            trigger: 'input[name="study_school"]',
            run: "text UCL",
        },
        {
            content: "School Level",
            trigger: 'input[name="study_field"]',
            run: "text Civil Engineering, Applied Mathematics",
        },
        {
            content: "Set Seniority at Hiring",
            trigger: 'input[name="l10n_be_scale_seniority"]',
            run: "text 1",
        },
        {
            content: "Bank Account",
            trigger: 'input[name="acc_number"]',
            run: "text BE10 3631 0709 4104",
        },
        {
            content: "Private License Plate",
            trigger: 'input[name="private_car_plate"]',
            run: "text 1-ABC-123",
        },
        {
            content: "Emergency Contact",
            trigger: 'input[name="emergency_contact"]',
            run: "text Batman",
        },
        {
            content: "Emergency Phone",
            trigger: 'input[name="emergency_phone"]',
            run: "text +32 2 290 34 90",
        },
        {
            content: "Nationality",
            trigger: "label[for=country_id]:eq(0)",
            run: function () {
                $("select[name=country_id] option:contains(Belgium)").prop("selected", true);
                $("select[name=country_id]").trigger("change");
            },
        },
        {
            content: "Country of Birth",
            trigger: "label[for=country_of_birth]:eq(0)",
            run: function () {
                $("select[name=country_of_birth] option:contains(Belgium)").prop("selected", true);
                $("select[name=country_of_birth]").trigger("change");
            },
        },
        {
            content: "Country",
            trigger: "label[for=country_id]:eq(0)",
            run: function () {
                $("select[name=country] option:contains(Belgium)").prop("selected", true);
                $("select[name=country]").trigger("change");
            },
        },
        {
            content: "Lang",
            trigger: "label[for=lang]:eq(0)",
            run: function () {
                $("select[name=lang] option:contains(English)").prop("selected", true);
                $("select[name=lang]").trigger("change");
            },
        },
        {
            content: "Check Disabled",
            trigger: "input[name='disabled']",
            run: "click",
        },
        {
            content: "Uncheck Disabled",
            trigger: "input[name='disabled']",
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: "click",
        },
        {
            content: "Set Married",
            trigger: "label[for=marital]",
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: function () {
                $("select[name=marital] option:contains(Married)").prop("selected", true);
                $("select[name=marital]").trigger("change");
            },
        },
        {
            content: "Check Disabled Spouse Bool",
            trigger: "input[name=disabled_spouse_bool]",
            extra_trigger: 'input[name="Net"][value="2431.1"]',
            run: "click",
        },
        {
            content: "Uncheck Disabled Spouse Bool",
            trigger: "input[name=disabled_spouse_bool]",
            extra_trigger: 'input[name="Net"][value="2431.1"]',
            run: "click",
        },
        {
            content: "Set High Spouse Income",
            trigger: "label[for=spouse_fiscal_status]",
            extra_trigger: 'input[name="Net"][value="2431.1"]',
            run: function () {
                $('select[name=spouse_fiscal_status] option:contains("With High Income")').prop(
                    "selected",
                    true
                );
                $("select[name=spouse_fiscal_status]").trigger("change");
            },
        },
        {
            content: "Unset Married",
            trigger: "label[for=marital]",
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: function () {
                $("select[name=marital] option:contains(Single)").prop("selected", true);
                $("select[name=marital]").trigger("change");
            },
        },
        {
            content: "Set Children",
            trigger: "input[name=children]",
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: "text 3",
        },
        {
            content: "Check Disabled Children",
            trigger: "input[name=disabled_children_bool]",
            extra_trigger: 'input[name="Net"][value="2444.69"]',
            run: "click",
        },
        {
            content: "Set 1 Disabled Children",
            trigger: "input[name=disabled_children_number]",
            extra_trigger: 'input[name="Net"][value="2444.69"]',
            run: "text 1",
        },
        {
            content: "Set 0 Disabled Children",
            trigger: "input[name=disabled_children_number]",
            extra_trigger: 'input[name="Net"][value="2663.69"]',
            run: function (actions) {
                actions.text("0", this.$anchor);
                this.$anchor.trigger("blur");
            },
        },
        {
            content: "Uncheck Disabled Children",
            trigger: "input[name=disabled_children_bool]",
            extra_trigger: 'input[name="Net"][value="2444.69"]',
            run: "click",
        },
        {
            content: "Unset Children",
            trigger: "input[name=children]",
            extra_trigger: 'input[name="Net"][value="2444.69"]',
            run: "text 0",
        },
        {
            content: "Check Other Dependent People",
            trigger: "input[name=other_dependent_people]",
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: "click",
        },
        {
            content: "Set 2 Senior",
            trigger: "input[name=other_senior_dependent]",
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: "text 2",
        },
        {
            content: "Set 1 disabled Senior",
            trigger: "input[name=other_disabled_senior_dependent]",
            extra_trigger: 'input[name="Net"][value="2282.69"]',
            run: "text 1",
        },
        {
            content: "Set 2 Juniors",
            trigger: "input[name=other_juniors_dependent]",
            extra_trigger: 'input[name="Net"][value="2366.69"]',
            run: "text 2",
        },
        {
            content: "Set 1 disabled Junior",
            trigger: "input[name=other_disabled_juniors_dependent]",
            extra_trigger: 'input[name="Net"][value="2444.69"]',
            run: "text 1",
        },
        {
            content: "Unset 1 disabled Senior over 2",
            trigger: "input[name=other_disabled_juniors_dependent]",
            extra_trigger: 'input[name="Net"][value="2483.69"]',
            run: "text 0",
        },
        {
            content: "Unset 2 Juniors",
            trigger: "input[name=other_juniors_dependent]",
            extra_trigger: 'input[name="Net"][value="2444.69"]',
            run: "text 0",
        },
        {
            content: "Unset 1 disabled Senior",
            trigger: "input[name=other_disabled_senior_dependent]",
            extra_trigger: 'input[name="Net"][value="2366.69"]',
            run: "text 0",
        },
        {
            content: "Unset 2 Seniors",
            trigger: "input[name=other_senior_dependent]",
            extra_trigger: 'input[name="Net"][value="2282.69"]',
            run: "text 0",
        },
        {
            content: "Uncheck Other Dependent People",
            trigger: "input[name=other_dependent_people]",
            extra_trigger: 'input[name="Net"][value="2114.69"]',
            run: "click",
        },
        {
            content: "Choose a car",
            trigger: 'input[name="fold_company_car_total_depreciated_cost"]',
            extra_trigger: 'input[name="Gross"][value="3000"]',
            run: "click",
        },
        {
            content: "Choose a new car",
            trigger: "label[for=company_car_total_depreciated_cost]",
            run: function () {
                $(
                    'select[name="select_company_car_total_depreciated_cost"] option:contains(Opel)'
                ).prop("selected", true);
                $('select[name="select_company_car_total_depreciated_cost"]').trigger("change");
            },
        },
        // set personal info
        {
            content: "Upload ID card copy (Both Sides)",
            trigger: 'input[name="id_card"]',
            async run() {
                await inputFiles('input[name="id_card"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_id_card.pdf",
                    }),
                ]);
            },
        },
        {
            content: "Upload Mobile Subscription Invoice",
            trigger: 'input[name="mobile_invoice"]',
            async run() {
                await inputFiles('input[name="mobile_invoice"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_mobile_invoice.pdf",
                    }),
                ]);
            },
        },
        {
            content: "Upload Sim Card Copy",
            trigger: 'input[name="sim_card"]',
            async run() {
                await inputFiles('input[name="sim_card"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_sim_card.pdf",
                    }),
                ]);
            },
        },
        {
            content: "Upload Internet Subscription invoice",
            trigger: 'input[name="internet_invoice"]',
            async run() {
                await inputFiles('input[name="internet_invoice"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_internet_invoice.pdf",
                    }),
                ]);
            },
        },
        {
            content: "Upload Driving License",
            trigger: 'input[name="driving_license"]',
            async run() {
                await inputFiles('input[name="driving_license"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_driving_license.pdf",
                    }),
                ]);
            },
        },
        {
            content: "submit",
            trigger: "button#hr_cs_submit",
            extra_trigger: 'input[name="Gross"][value="2671.14"]',
            run: "click",
        },
        {
            content: "Next 1",
            trigger: "iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Type Date",
            trigger: "iframe input.ui-selected",
            run: "text 17/09/2018",
        },
        {
            content: "Next 2",
            trigger: "iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Type Number",
            trigger: "iframe input.ui-selected",
            run: "text 58/4",
        },
        // fill signature
        {
            content: "Next 3",
            trigger: "iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Click Signature",
            trigger: "iframe button.o_sign_sign_item",
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
            trigger: "iframe body:not(:has(footer.modal-footer button.btn-primary))",
            run: function () {},
        },
        // fill date
        {
            content: "Next 4",
            trigger: 'iframe .o_sign_sign_item_navigator:contains("next")',
            run: "click",
        },
        {
            content: "Type Date",
            trigger: "iframe input.ui-selected",
            run: function (actions) {
                var self = this;
                setTimeout(function () {
                    actions.text("17/09/2018", self.$anchor);
                }, 10);
            },
        },
        {
            content: "Validate and Sign",
            trigger: ".o_sign_validate_banner button",
            run: "click",
        },
    ],
});
registry.category("web_tour.tours").add("hr_contract_salary_tour_hr_sign", {
    test: true,
    url: "/web",
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
                ".o_menu_systray .o_switch_company_menu .dropdown-item div span:contains('My Belgian Company - TEST')",
            run: "click",
        },
        {
            content: "Recruitment",
            trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
            extra_trigger:
                ".o_menu_systray .o_switch_company_menu button.dropdown-toggle span:contains('My Belgian Company - TEST')",
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
        },
        {
            content: "Open Application Pipe",
            trigger: "button.oe_stat_button:contains(Applications)",
            extra_trigger: ".o_form_saved",
            run: "click",
        },
        {
            content: "Select Our Applicant",
            trigger: 'div.o_kanban_view b.o_kanban_record_title:contains("Mitchell Admin 2")',
        },
        {
            content: "Open Contracts",
            trigger: "button.oe_stat_button:contains(Contracts)",
            extra_trigger: ".o_form_saved",
            run: "click",
        },
        {
            content: "Open Signature Request",
            trigger: "button.oe_stat_button:contains(Sign)",
            extra_trigger: ".o_form_saved",
            run: "click",
        },
        {
            content: "Sign",
            trigger: "button:contains(Sign Document)",
            run: "click",
        },
        {
            content: "Next 5",
            trigger: "iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Click Signature",
            trigger: "iframe button.o_sign_sign_item",
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
    test: true,
    url: "/web",
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
                ".o_menu_systray .o_switch_company_menu .dropdown-item div span:contains('My Belgian Company - TEST')",
            run: "click",
        },
        {
            content: "Recruitment",
            trigger: '.o_app[data-menu-xmlid="hr_recruitment.menu_hr_recruitment_root"]',
            extra_trigger:
                ".o_menu_systray .o_switch_company_menu button.dropdown-toggle span:contains('My Belgian Company - TEST')",
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
        },
        {
            content: "Open Application Pipe",
            trigger: "button.oe_stat_button:contains(Applications)",
            extra_trigger: ".o_form_saved",
            run: "click",
        },
        {
            content: "Create Applicant",
            trigger: ".o-kanban-button-new",
            extra_trigger: '.o_breadcrumb .active:contains("Applications")',
            run: "click",
        },
        {
            content: "Application Name",
            trigger: '.oe_title [name="name"] textarea',
            run: "text Mitchell's Application",
        },
        {
            content: "Applicant's Name",
            trigger: '.oe_title [name="partner_name"] input',
            run: "text Mitchell Admin 3",
        },
        {
            content: "Add Email Address",
            trigger: '.o_group [name="email_from"] input',
            run: "text mitchell2.stephen@example.com",
        },
        {
            content: "Confirm Applicant Creation",
            trigger: ".o_control_panel button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_statusbar_status button.dropdown-toggle",
            content: "Move applicant to hired stage",
            run: "click",
        },
        {
            content: "Recruitment",
            trigger: '.dropdown-item:contains("Contract Signed")',
            run: "click",
        },
        {
            content: "Create Employee",
            trigger: ".o_statusbar_buttons > button[name='create_employee_from_applicant']",
            extra_trigger: ".o_statusbar_buttons",
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
                ".o_field_widget.o_field_many2one_avatar_user.o_field_many2one_avatar[name=parent_id]",
            run: function (actions) {
                actions.text("Mitchell", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains(Mitchell)",
            auto: true,
        },
        {
            content: "Add Work Email",
            trigger: '.o_group [name="work_email"] input',
            run: "text mitchel3_work@example.com",
        },
        {
            content: "Save Employee",
            trigger: ".o_form_button_save",
            extra_trigger: '.o-mail-Message-body a[href*="/web#action=hr.plan_wizard_action"]',
            run: "click",
        },
        {
            content: "Create Contract",
            trigger: '.o-form-buttonbox .oe_stat_button:contains("Contracts")',
            extra_trigger: ".o_form_saved",
            run: "click",
        },
        {
            content: "Contract Reference",
            trigger: '.modal-content .o_field_widget[name="name"] input',
            run: "text Mitchell Admin PFI Contract",
        },
        {
            content: "Salary Structure Type",
            trigger: ".modal-content .o_field_widget.o_field_many2one[name=structure_type_id]",
            run: function (actions) {
                actions.text("CP200: Belgian Employee", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains('CP200: Belgian Employee')",
            auto: true,
        },
        {
            content: "Select Contract Details Tab",
            trigger: ".o_notebook ul > li > a:contains(Contract)",
            run: "click",
        },
        {
            content: "HR Responsible",
            trigger:
                "div.o_field_widget.o_required_modifier.o_field_many2one_avatar_user.o_field_many2one_avatar[name=hr_responsible_id]",
            run: function (actions) {
                actions.text("Laurie Poiret", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains('Laurie Poiret')",
            auto: true,
        },
        {
            content: "Contract Update Template",
            trigger: ".o_field_widget.o_field_many2one[name=contract_update_template_id]",
            run: function (actions) {
                actions.text("test_employee_contract", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains('test_employee_contract')",
            auto: true,
        },
        {
            content: "New Contract Document Template",
            trigger: ".o_field_widget.o_field_many2one[name=sign_template_id]",
            run: function (actions) {
                actions.text("test_employee_contract", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains('test_employee_contract')",
            auto: true,
        },
        {
            content: "Select Salary Information Tab",
            trigger: ".o_notebook ul > li > a:contains(Salary)",
            run: "click",
        },
        {
            content: "Contract Information",
            trigger: "div[name='wage'] input",
            run: "text 2950",
        },
        {
            content: "Contract Information",
            trigger: "div.o_field_boolean[name='transport_mode_car'] input",
            run: "click",
        },
        {
            content: "Contract Information",
            trigger: ".o_field_widget.o_field_many2one[name=car_id]",
            run: function (actions) {
                actions.text("JFC", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains('1-JFC-095')",
            auto: true,
        },
        {
            content: "Contract Information",
            trigger: "div[name='fuel_card'] input",
            run: "text 250",
        },
        {
            content: "Contract Information",
            trigger: "div[name='commission_on_target'] input",
            run: "text 1000",
        },
        {
            content: "Contract Information",
            trigger: "[name='ip_wage_rate'] input",
            run: "text 25",
        },
        {
            content: "Contract Information",
            trigger: "div.o_field_boolean[name='ip'] input",
            run: "click",
        },
        {
            content: "Save Contract",
            trigger: ".modal-content .o_form_button_save",
            run: "click",
        },
        {
            content: "Go on Contract",
            trigger: '.o-form-buttonbox .oe_stat_button:contains("In Contract Since")',
            run: "click",
        },
        {
            content: "Generate Simulation Link",
            trigger: ".o_statusbar_buttons > button:contains('Generate Offer')",
            extra_trigger: ".o_statusbar_buttons",
            run: "click",
        },
        {
            content: "Select Contract",
            trigger: ".o_field_widget.o_field_many2one[name=contract_id]",
            run: function (actions) {
                actions.text("Mitchell Admin PFI", this.$anchor.find("input"));
            },
        },
        {
            trigger: ".ui-autocomplete > li > a:contains('Mitchell Admin PFI Contract')",
            auto: true,
        },
        {
            content: "Send Offer",
            trigger: "button[name='action_send_offer']",
            extra_trigger: "div.modal-content",
            run: "click",
        },
        {
            content: "Send Offer",
            trigger: "button[name='action_send_mail']",
            extra_trigger: ".modal-dialog .btn-primary:contains('Send')",
            run: "click",
        },
        {
            content: "Click on Offers Stat Button",
            trigger: "button[name='action_show_offers']",
            run: "click",
        },
        {
            content: "Go on configurator",
            trigger: ".o-mail-Chatter .o-mail-Message:eq(0) a",
            run: function () {
                var simulation_link = $(".o-mail-Chatter .o-mail-Message:eq(0) a")[0].href;
                // Retrieve the link without the origin to avoid
                // mismatch between localhost:8069 and 127.0.0.1:8069
                // when running the tour with chrome headless
                var regex = "/salary_package/simulation/.*";
                var url = simulation_link.match(regex)[0];
                window.location.href = window.location.origin + url;
            },
            extra_trigger: "button[name='action_jump_to_offer']",
        },
        {
            content: "Unchoose default car",
            trigger: 'input[name="fold_company_car_total_depreciated_cost"]',
            run: "click",
        },
        {
            content: "Choose to be in waiting list for car",
            trigger: 'input[name="fold_wishlist_car_total_depreciated_cost"]',
            run: "click",
        },
        {
            content: "Choose a new car in waiting list",
            trigger: "label[for=wishlist_car_total_depreciated_cost]",
            run: function () {
                $(
                    'select[name="select_wishlist_car_total_depreciated_cost"] option:contains(a3)'
                ).prop("selected", true);
                $('select[name="select_wishlist_car_total_depreciated_cost"]').trigger("change");
            },
        },
        {
            content: "BirthDate",
            trigger: 'input[name="birthday"]',
            run: function () {
                $("input[name='birthday']").val("2017-09-01");
            },
        },
        {
            content: "Gender",
            trigger: 'input[name="gender"]',
            run: function () {
                $('input[value="female"]').prop("checked", true);
            },
        },
        {
            content: "National Identification Number",
            trigger: 'input[name="identification_id"]',
            run: "text 11.11.11-111.11",
        },
        {
            content: "Street",
            trigger: 'input[name="private_street"]',
            run: "text Rue des Wallons",
        },
        {
            content: "City",
            trigger: 'input[name="private_city"]',
            run: "text Louvain-la-Neuve",
        },
        {
            content: "Zip Code",
            trigger: 'input[name="private_zip"]',
            run: "text 1348",
        },
        {
            content: "Email",
            trigger: 'input[name="private_email"]',
            run: "text mitchell2.stephen@example.com",
        },
        {
            content: "Phone Number",
            trigger: 'input[name="private_phone"]',
            run: "text 1234567890",
        },
        {
            content: "Place of Birth",
            trigger: 'input[name="place_of_birth"]',
            run: "text Brussels",
        },
        {
            content: "KM Home/Work",
            trigger: 'input[name="km_home_work"]',
            run: "text 75",
        },
        {
            content: "Certificate",
            trigger: "label[for=certificate]",
            run: function () {
                $("select[name=certificate] option:contains(Master)").prop("selected", true);
                $("select[name=certificate]").trigger("change");
            },
        },
        {
            content: "School",
            trigger: 'input[name="study_school"]',
            run: "text UCL",
        },
        {
            content: "School Level",
            trigger: 'input[name="study_field"]',
            run: "text Civil Engineering, Applied Mathematics",
        },
        {
            content: "Set Seniority at Hiring",
            trigger: 'input[name="l10n_be_scale_seniority"]',
            run: "text 1",
        },
        {
            content: "Lang",
            trigger: "label[for=lang]:eq(0)",
            run: function () {
                $("select[name=lang] option:contains(English)").prop("selected", true);
                $("select[name=lang]").trigger("change");
            },
        },
        {
            content: "Bank Account",
            trigger: 'input[name="acc_number"]',
            run: "text BE10 3631 0709 4104",
        },
        {
            content: "Bank Account",
            trigger: 'input[name="emergency_contact"]',
            run: "text Batman",
        },
        {
            content: "Bank Account",
            trigger: 'input[name="emergency_phone"]',
            run: "text +32 2 290 34 90",
        },
        {
            content: "Nationality",
            trigger: "label[for=country_id]:eq(0)",
            run: function () {
                $("select[name=country_id] option:contains(Belgium)").prop("selected", true);
                $("select[name=country_id]").trigger("change");
            },
        },
        {
            content: "Country of Birth",
            trigger: "label[for=country_of_birth]",
            run: function () {
                $("select[name=country_of_birth] option:contains(Belgium)").prop("selected", true);
                $("select[name=country_of_birth]").trigger("change");
            },
        },
        {
            content: "Country",
            trigger: "label[for=private_country_id]:eq(0)",
            run: function () {
                $("select[name=private_country_id] option:contains(Belgium)").prop(
                    "selected",
                    true
                );
                $("select[name=private_country_id]").trigger("change");
            },
        },
        {
            content: "Set 0 Children",
            trigger: "input[name=children]",
            run: "text 0",
        },
        // set personal info
        {
            content: "Upload ID card copy (Both Sides)",
            trigger: 'input[name="id_card"]',
            async run() {
                await inputFiles('input[name="id_card"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_id_card.pdf",
                    }),
                ]);
            },
        },
        {
            content: "Upload Mobile Subscription Invoice",
            trigger: 'input[name="mobile_invoice"]',
            async run() {
                await inputFiles('input[name="mobile_invoice"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_mobile_invoice.pdf",
                    }),
                ]);
            },
        },
        {
            content: "Upload Sim Card Copy",
            trigger: 'input[name="sim_card"]',
            async run() {
                await inputFiles('input[name="sim_card"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_sim_card.pdf",
                    }),
                ]);
            },
        },
        {
            content: "Upload Internet Subscription invoice",
            trigger: 'input[name="internet_invoice"]',
            async run() {
                await inputFiles('input[name="internet_invoice"]', [
                    await createFile({
                        content: "hello, world",
                        contentType: "application/pdf",
                        name: "employee_internet_invoice.pdf",
                    }),
                ]);
            },
        },
        {
            content: "submit",
            trigger: "button#hr_cs_submit",
            run: "click",
        },
        {
            content: "Next 6",
            trigger: "iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Type Date",
            trigger: "iframe input.ui-selected",
            run: "text 17/09/2018",
        },
        {
            content: "Next 7",
            trigger: "iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Type Number",
            trigger: "iframe input.ui-selected",
            run: "text 58/4",
        },
        // fill signature
        {
            content: "Next 8",
            trigger: "iframe .o_sign_sign_item_navigator",
            run: "click",
        },
        {
            content: "Click Signature",
            trigger: "iframe button.o_sign_sign_item",
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
            trigger: "iframe body:not(:has(footer.modal-footer button.btn-primary))",
            run: function () {},
        },
        // fill date
        {
            content: "Next 9",
            trigger: 'iframe .o_sign_sign_item_navigator:contains("next")',
            run: "click",
        },
        {
            content: "Type Date",
            trigger: "iframe input.ui-selected",
            run: function (actions) {
                var self = this;
                setTimeout(function () {
                    actions.text("17/09/2018", self.$anchor);
                }, 10);
            },
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
                window.location.href = window.location.origin + "/web";
            },
        },
        {
            content: "Check home page is loaded",
            trigger: "a.o_app.o_menuitem",
            run: function () {},
        },
    ],
});
