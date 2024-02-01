/** @odoo-module **/
    
    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";

    registry.category("web_tour.tours").add('hr_expense_test_tour', {
        test: true,
        url: "/web",
        steps: () => [stepUtils.showAppsMenuItem(),
        {
            content: "Go to Expense",
            trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
        },
        {
            content: "Go to My Expenses",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_my_expenses"]',
        },
        {
            content: "Go to My Expenses to Report",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_my_expenses_to_submit"]',
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
            content: "Go to kanban view",
            trigger: "button.o_switch_view.o_kanban",
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
            content: "Go to Reporting",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_reports"]',
        },
        {
            content: "Go to Expenses Analysis",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_all_expenses"]',
        },
        {
            content: "Check Upload Button",
            trigger: 'li.breadcrumb-item:contains("Expenses Analysis")',
            run() {
                const button = document.querySelector('.o_button_upload_expense');
                if(!button) {
                    console.error('Missing Upload button in Expenses Analysis > List View');
                }
            }
        },
        {
            content: "Go to kanban view",
            trigger: "button.o_switch_view.o_kanban",
        },
        {
            content: "Check Upload Button",
            trigger: "button.o_switch_view.o_kanban.active",
            run() {
                const button = document.querySelector('.o_button_upload_expense');
                if(!button) {
                    console.error('Missing Upload button in Expenses Analysis > Kanban View');
                }
            }
        },
    ]});

    registry.category("web_tour.tours").add('hr_expense_access_rights_test_tour', {
        test: true,
        url: "/web",
        steps: () => [stepUtils.showAppsMenuItem(),
        {
            content: "Go to Expense",
            trigger: '.o_app[data-menu-xmlid="hr_expense.menu_hr_expense_root"]',
        },
        {
            content: "Go to My Expenses",
            trigger: 'button[data-menu-xmlid="hr_expense.menu_hr_expense_my_expenses"]',
        },
        {
            content: "Go to My Reports",
            trigger: 'a[data-menu-xmlid="hr_expense.menu_hr_expense_sheet_my_reports"]',
        },
        {
            content: "Go to First Expense for employee",
            trigger: 'td[data-tooltip="First Expense for employee"]',
        },
        {
            content: "Click Submit to Manager Button",
            trigger: '.o_expense_sheet_submit',
        },
        {
            content: 'Verify the expene sheet is submitted',
            trigger: '.o_arrow_button_current:contains("Submitted")',
            isCheck: true,
        },
    ]});
