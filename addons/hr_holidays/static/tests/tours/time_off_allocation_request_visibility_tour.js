import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("time_off_allocation_request_hidden_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: ".o_app[data-menu-xmlid='hr_holidays.menu_hr_holidays_root']",
            run: "click",
        },
        {
            content: "Click New in My Time calendar, a plain button without dropdown",
            trigger:
                ".o_calendar_view .o_control_panel_main_buttons:not(:has(.o-dropdown-caret)) button.btn-primary:contains('New')",
            run: "click",
        },
        {
            content: "Verify New opens the time off form directly",
            trigger: ".modal .modal-title:contains('New Time Off')",
        },
        {
            content: "Discard the time off form",
            trigger: ".modal .o_form_button_cancel",
            run: "click",
        },
        {
            content: "Click on the Time Off dashboard card",
            trigger: "body:not(:has(.modal)) .o_timeoff_card_inner",
            run: "click",
        },
        {
            content: "Click on Allocated in card popover",
            trigger: ".o_popover .btn-link:contains('Allocated')",
            run: "click",
        },
        {
            content: "Verify Allocated list view renders without New button",
            trigger: ".o_list_view:has(.o_list_renderer):not(:has(.o_list_button_add))",
        },
        {
            content: "Open My Time menu",
            trigger: ".o-dropdown[data-menu-xmlid='hr_holidays.menu_hr_holidays_my_leaves']",
            run: "click",
        },
        {
            content: "Open My Time > Requests",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_holidays.menu_open_allocation']",
            run: "click",
        },
        {
            content: "Verify My Time > Requests list view renders without New button",
            trigger: ".o_list_view:has(.o_switch_view.o_kanban):not(:has(.o_list_button_add))",
        },
        {
            content: "Switch to Kanban view",
            trigger: ".o_switch_view.o_kanban",
            run: "click",
        },
        {
            content: "Verify My Time > Requests kanban view renders without New button",
            trigger: ".o_kanban_view:has(.o_kanban_renderer):not(:has(.o-kanban-button-new))",
        },
    ],
});

registry.category("web_tour.tours").add("time_off_allocation_request_visible_tour", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Time Off app",
            trigger: ".o_app[data-menu-xmlid='hr_holidays.menu_hr_holidays_root']",
            run: "click",
        },
        {
            content: "Open New dropdown in My Time calendar",
            trigger: ".o_calendar_view .o-dropdown-caret",
            run: "click",
        },
        {
            content: "Verify New Allocation Request is shown",
            trigger: ".o-dropdown--menu .o-dropdown-item:contains('New Allocation Request')",
        },
        {
            content: "Close New dropdown",
            trigger: ".o_calendar_view .o-dropdown-caret",
            run: "click",
        },
        {
            content: "Click on the Time Off dashboard card",
            trigger: ".o_timeoff_card_inner",
            run: "click",
        },
        {
            content: "Click on Allocated in card popover",
            trigger: ".o_popover .btn-link:contains('Allocated')",
            run: "click",
        },
        {
            content: "Verify Allocated list view shows New button",
            trigger: ".o_list_view .o_list_button_add",
        },
        {
            content: "Open My Time menu",
            trigger: ".o-dropdown[data-menu-xmlid='hr_holidays.menu_hr_holidays_my_leaves']",
            run: "click",
        },
        {
            content: "Open My Time > Requests",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_holidays.menu_open_allocation']",
            run: "click",
        },
        {
            content: "Verify My Time > Requests list view shows New button",
            trigger: ".o_list_view:has(.o_switch_view.o_kanban) .o_list_button_add",
        },
        {
            content: "Switch to Kanban view",
            trigger: ".o_switch_view.o_kanban",
            run: "click",
        },
        {
            content: "Verify My Time > Requests kanban view shows New button",
            trigger: ".o_kanban_view .o-kanban-button-new",
        },
    ],
});
