import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("configurator_params_step", {
    steps: () => [
        {
            content: "Check if we are at the theme selection screen",
            trigger: ".o_theme_selection_screen",
        },
    ],
});
