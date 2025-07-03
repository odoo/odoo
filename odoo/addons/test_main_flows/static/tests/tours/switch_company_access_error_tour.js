import { router } from "@web/core/browser/router";
import { registry } from "@web/core/registry";

const _console = window.console;
function assertEqual(actual, expected, msg = "") {
    if (actual !== expected) {
        const description = msg ? ` ${msg}` : "";
        _console.error(`Assert failed: expected: ${expected} ; got: ${actual}.${description}`);
    }
}

registry.category("web_tour.tours").add("test_company_switch_access_error", {
    steps: () => [
        {
            trigger: ".o_view_controller.o_list_view .o_data_cell:contains(p1)",
        },
        {
            trigger: ".o_view_controller.o_list_view .o_data_cell:contains(p2)",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_last_breadcrumb_item:contains(p2)",
        },
        {
            trigger: ".o_switch_company_menu button",
            run: "click",
        },
        {
            trigger: ".o_switch_company_item:contains(second company) [role=menuitemcheckbox]",
            run: "click",
        },
        {
            trigger: ".o_switch_company_menu_buttons button:contains(Confirm)",
            run: "click",
            expectUnloadPage: true,
        },
        {
            trigger: ".o_view_controller.o_list_view",
            run: "click",
        },
        {
            trigger: "header.o_navbar .o_menu_brand:contains(model_multicompany_menu)",
        },
        {
            trigger: ".o_view_controller.o_list_view .o_data_cell:contains(p1)",
            async run() {
                assertEqual("action" in router.current, true);
            },
        },
    ],
});
