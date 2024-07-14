/** @odoo-module */
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_web_studio.test_disable_approvals", {
    sequence: 1260,
    test: true,
    steps: () => [
        {
            trigger: ".o_web_studio_view_renderer .o_view_controller.o_form_view button.mybutton",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='studio_approval']:checked",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='studio_approval']:not(:checked)",
            isCheck: true,
        },
    ],
});
