import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_web.test_apply_to_all", {
    steps: () => [
        {
            trigger: ".o_field_text textarea",
            run: "click",
        },
        {
            trigger: ".o-translate-button",
            run: "click",
        },
        {
            trigger: ".o_translation_dialog textarea#fr_FR",
            run: "edit paul bismuth"
        },
        {
            trigger: ".o_translation_dialog .o-dropdown.dropdown-toggle",
            run: "click"
        },
        {
            trigger: ".o_popover .dropdown-item",
            run: "click",
        },
        {
            trigger: ".o_translation_dialog footer button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_field_text textarea:value(Paul Bismuth)",
        }
    ]
});

registry.category("web_tour.tours").add("test_web.test_with_html_editor", {
    steps: () => [
        {
            trigger: ".o_field_html .odoo-editor-editable",
            run: "click",
        },
        {
            trigger: ".o-translate-button",
            run: "click",
        },
        {
            trigger: ".o_translation_dialog .o-translate-lang-buttons button:contains(English)",
            run: "click",
        },
        {
            trigger: ".o_translation_dialog .o-translate-lang-buttons button.active:contains(English)",
        },
        {
            trigger: ".o_translation_dialog .o_field_html:eq(0) .odoo-editor-editable",
            run: "editor nouvelle valeur"
        },
        {
            trigger: ".o_translation_dialog .o_field_html:eq(1) .odoo-editor-editable",
            run: "editor some other relevant value in english"
        },
        {
            trigger: ".o_translation_dialog footer button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_field_html .odoo-editor-editable:contains(nouvelle valeur)",
        }
    ]
});
