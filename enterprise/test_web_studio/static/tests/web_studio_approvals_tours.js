import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_web_studio.test_disable_approvals", {
    steps: () => [
        {
            trigger: ".o_web_studio_view_renderer .o_view_controller.o_form_view button.mybutton",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar_approval .o_approval_archive",
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("test_web_studio.test_disable_approvals_via_kanban", {
    steps: () => [
        {
            trigger: ".o_web_studio_view_renderer .o_view_controller.o_form_view button.mybutton",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer .o_view_controller.o_form_view button.mybutton .o_web_studio_approval_avatar",
        },
        {
            trigger: ".o_web_studio_sidebar_approval .o_studio_sidebar_approval_rule",
        },
        {
            trigger: ".o_web_studio_sidebar_approval button i.oi-view-kanban",
            run: "click",
        },
        {
            trigger: ".o_kanban_view .o_kanban_record",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_cp_action_menus button",
            run: "click",
        },
        {
            trigger: ".o-main-components-container .dropdown-item:contains('archive')",
            run: "click",
        },
        {
            trigger: ".modal button:contains('Archive')",
            run: "click",
        },
        {
            trigger: ".o_web_studio_breadcrumb li.active:contains('Form')",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar_approval",
            run({ anchor }) {
                if (anchor.querySelector(".o_studio_sidebar_approval_rule")) {
                    throw new Error("No approval rule should be visible")
                }
            },
        },
    ],
});
