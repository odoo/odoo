/** @odoo-module **/
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
    test: true,
    steps: () => [
        {
            trigger: ".o_list_view",
            run() {
                assertEqual(
                    JSON.stringify(
                        Array.from(this.anchor.querySelectorAll(".o_data_cell")).map(
                            (n) => n.innerText
                        )
                    ),
                    JSON.stringify(["p1", "p2"])
                );
            },
        },
        {
            trigger: ".o_list_view .o_data_cell:contains(p2)",
        },
        {
            trigger: ".o_form_view .o_last_breadcrumb_item:contains(p2)",
            isCheck: true,
        },
        {
            trigger: ".o_switch_company_menu button",
        },
        {
            trigger: ".o-dropdown--menu .dropdown-item:contains(second company) .toggle_company",
        },
        {
            trigger: ".o_view_controller.o_list_view",
        },
        {
            trigger: ".o_view_controller.o_list_view",
            async run() {
                assertEqual(
                    JSON.stringify(
                        Array.from(this.anchor.querySelectorAll(".o_data_cell")).map(
                            (n) => n.innerText
                        )
                    ),
                    JSON.stringify(["p1"])
                );
                assertEqual(
                    document.querySelector("header.o_navbar .o_menu_brand").innerText,
                    "model_multicompany_menu"
                );
                assertEqual("action" in router.current, true);
            },
            isCheck: true,
        },
    ],
});
