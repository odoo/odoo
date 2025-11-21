import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";


registry.category("web_tour.tours").add("change_expense_category_price_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("hr_expense.menu_hr_expense_root", "Go to the Expenses app"),
        {
            content: "Open the Configuration menu",
            trigger: ".o-dropdown[data-menu-xmlid='hr_expense.menu_hr_expense_configuration']",
            run: "click",
        },
        {
            content: "Open the Expense Categories",
            trigger: ".o-dropdown-item[data-menu-xmlid='hr_expense.menu_hr_product']",
            run: "click",
        },
        {
            content: "Open the product A",
            trigger: ".o_data_row .o_data_cell[data-tooltip='product_a']",
            run: "click",
        },
        {
            content: "Change the price to 2",
            trigger: "input#standard_price_0",
            run: "edit 2",
        },
        {
            // We need this to unfocus the input, otherwise it's too quick and the new_standard_price is set to the old value.
            content: "Unfocus the input to register the change",
            trigger: ".o_form_label",
            run: "click",
        },
        {
            content: "Save the changes",
            trigger: ".o_form_button_save:enabled",
            run: "click",
        },
        {
            content: "Wait until the form is saved",
            trigger: "body .modal-footer:has(.btn-primary)",
        },
        {
            content: "Confirm the changes",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Go back to the list of categories",
            trigger: ".breadcrumb-item:contains('Expense Categories')",
            run: "click",
        },
        {
            content: "Open the product B",
            trigger: ".o_data_row .o_data_cell[data-tooltip='product_b']",
            run: "click",
        },
        {
            content: "Change the price to 6",
            trigger: "input#standard_price_0",
            run: "edit 6",
        },
        {
            content: "Unfocus the input to register the change",
            trigger: ".o_form_label",
            run: "click",
        },
        {
            content: "Save the changes",
            trigger: ".o_form_button_save:enabled",
            run: "click",
        },
        {
            content: "Wait until the form is saved",
            trigger: "body .modal-footer:has(.btn-primary)",
        },
        {
            content: "Confirm the changes",
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            content: "Go back to the list of categories",
            trigger: ".breadcrumb-item:contains('Expense Categories')",
            run: "click",
        },
        {
            content: "Open the product C",
            trigger: ".o_data_row .o_data_cell[data-tooltip='product_c with no cost']",
            run: "click",
        },
        {
            content: "Change the price to 3",
            trigger: "input#standard_price_0",
            run: "edit 3",
        },
        {
            content: "Unfocus the input to register the change",
            trigger: ".o_form_label",
            run: "click",
        },
        {
            content: "Save the changes",
            trigger: ".o_form_button_save:enabled",
            run: "click",
        },
        {
            content: "Check that no warning is displayed",
            trigger: "body",
            run: () => {
                const warning = document.querySelector(".modal");
                if (warning) {
                    throw new Error("Warning should not be displayed when changing the price of a category with no linked expense.");
                }
            },
        },
        {
            content: "Go back to the list of categories",
            trigger: ".breadcrumb-item:contains('Expense Categories')",
            run: "click",
        },
        {
            content: "Wait until we are back to the list view",
            trigger: ".o_list_view",
        }
    ],
});
