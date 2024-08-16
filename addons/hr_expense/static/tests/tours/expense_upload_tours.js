/** @odoo-module **/
    
    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";

    registry.category("web_tour.tours").add('hr_expense_test_tour', {
        test: true,
        url: "/odoo",
        steps: () => [stepUtils.showAppsMenuItem(),
        {
            content: "Go to Expense",
            trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
            run: "click",
        },
        {
            content: "Go to My Expenses",
            trigger: 'button[data-menu-xmlid="hr_expense.menu_hr_expense_my_expenses"]',
            run: "click",
        },
        {
            content: "Go to My Expenses to Report",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_my_expenses_all"]',
            run: "click",
        },
        {
            content: "Check Upload Button",
            trigger: '.o_button_upload_expense',
            run() {
                const button = document.querySelector('.o_button_upload_expense');
                if(!button) {
                    console.error('Missing Upload button in My Expenses to Report > List View');
                }
            }
        },
        {
            content: "Create a new expense",
            trigger: "button.o_list_button_add",
            run: "click",
        },
        {
            content: "Enter category for new expense in Many2One field",
            trigger: ".o_field_widget.o_field_many2one[name=product_id] input",
            run: "edit [COMM] Communication",
        },
        {
            isActive: ["auto"],
            trigger: ".ui-autocomplete > li > a:contains('[COMM] Communication')",
            run: "click",
        },
        {
            content: "Enter a value for the total",
            trigger: "div[name=total_amount_currency] input",
            run: "edit 100",
        },
        {
            content: "Breadcrumb back to My Expenses",
            trigger: ".breadcrumb-item:contains('My Expenses')",
            run: "click",
        },
        {
            content: "Check Create Report Button, but not click on it",
            trigger: "button.o_switch_view.o_list.active",
            run() {
                const button = Array.from(document.querySelectorAll('.btn-secondary'))
                    .filter(element => element.textContent.includes('Create Report'));
                if(!button) {
                    console.error('Missing Create Report button in My Expenses to Report > List View');
                }
            }
        },
        {
            content: "Go to kanban view",
            trigger: "button.o_switch_view.o_kanban",
            run: "click",
        },
        {
            content: "Check Upload Button",
            trigger: "button.o_switch_view.o_kanban.active",
            run() {
                const button = document.querySelector('.o_button_upload_expense');
                if(!button) {
                    console.error('Missing Upload button in My Expenses to Report > Kanban View');
                }
            }
        },
        {
            content: "Check Create Report button and click on it",
            trigger: ".btn-secondary:contains(\"Create Report\")",
            run: "click"
        },
        {
            trigger: ".o_breadcrumb",
            run: "click",
        },
        {
            content: "Create Report button should not be visible anymore",
            trigger: '.o_control_panel_main:not(:contains(\"Create Report\"))',
        },
        {
            content: "Go to Reporting",
            trigger: 'button[data-menu-xmlid="hr_expense.menu_hr_expense_reports"]',
            run: "click",
        },
        {
            content: "Go to Expenses Analysis",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_all_expenses"]',
            run: "click",
        },
        {
            content: "Go to list view",
            trigger: "button.o_switch_view.o_list",
            run: "click",
        },
        {
            content: "Check Upload Button",
            trigger: "button.o_switch_view.o_list.active",
            run() {
                const button = document.querySelector('.o_button_upload_expense');
                if(!button) {
                    console.error('Missing Upload button in Expenses Analysis > List View');
                }
            }
        },
    ]});

    registry.category("web_tour.tours").add('hr_expense_access_rights_test_tour', {
        test: true,
        url: "/odoo",
        steps: () => [stepUtils.showAppsMenuItem(),
        {
            content: "Go to Expense",
            trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
            run: "click",
        },
        {
            content: "Go to My Expenses",
            trigger: 'button[data-menu-xmlid="hr_expense.menu_hr_expense_my_expenses"]',
            run: "click",
        },
        {
            content: "Go to My Reports",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_my_reports"]',
            run: "click",
        },
        {
            content: "Go to First Expense for employee",
            trigger: 'td[data-tooltip="First Expense for employee"]',
            run: "click",
        },
        {
            content: "Click Submit to Manager Button",
            trigger: '.o_expense_sheet_submit',
            run: "click",
        },
        {
            content: 'Verify the expene sheet is submitted',
            trigger: '.o_arrow_button_current:contains("Submitted")',
        },
    ]});
