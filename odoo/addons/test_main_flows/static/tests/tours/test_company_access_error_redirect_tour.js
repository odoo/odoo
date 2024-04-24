/** @odoo-module **/
import { cookie } from "@web/core/browser/cookie";
import { registry } from "@web/core/registry";

function assertEqual(actual, expected) {
    if (actual !== expected) {
        throw new Error(`Assert failed: expected: ${expected} ; got: ${actual}`);
    }
}

registry.category("web_tour.tours").add("test_company_access_error_redirect", {
    test: true,
    steps: () => [
        {
            trigger: ".o_form_view .o_last_breadcrumb_item:contains(p2)",
            isCheck: true,
        },
        {
            trigger: ".o_switch_company_menu button",
        },
        {
            trigger: ".o-dropdown--menu",
            run() {
                assertEqual(
                    document.querySelectorAll(".o-dropdown-item .toggle_company[aria-checked=true]")
                        .length,
                    2
                );
                assertEqual(
                    cookie.get("cids"),
                    [...document.querySelectorAll(".o-dropdown-item [data-company-id]")]
                        .flatMap((x) => x.getAttribute("data-company-id"))
                        .join("-")
                );
            },
        },
    ],
});
