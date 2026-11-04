import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("discuss_group_form_save_without_name.js", {
    steps: () => [
        {
            trigger: ".o_field_widget[name='description'] textarea",
            run: "edit Holiday plans && click .o_form_sheet",
        },
        {
            // Wait for the edit to apply, so that ".o_form_saved" can only match after the save.
            trigger: ".o_form_dirty",
        },
        { trigger: ".o_form_button_save", run: "click" },
        { trigger: ".o_form_saved" },
    ],
});
