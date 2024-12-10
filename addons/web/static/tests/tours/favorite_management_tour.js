import { queryAll } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_favorite_management", {
    url: "/odoo/apps",
    steps: () => [
        {
            trigger: ".o_facet_remove",
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            trigger: ".o_favorite_menu .o_accordion > .o_menu_item",
            run: "click",
        },
        {
            trigger: ".o_favorite_menu .o_accordion_values .o_input",
            run: "edit Apps1",
        },
        {
            trigger: ".o_save_favorite",
            run: "click",
        },
        {
            trigger: ".o_group_by_menu > .o-dropdown-item:contains(Category)",
            run: "click",
        },
        {
            trigger: ".o_favorite_menu .o_accordion_values .o_input",
            run: "edit Apps2",
        },
        {
            trigger: ".o_save_favorite",
            run: "click",
        },
        {
            trigger: ".o_favorite_menu .o-dropdown-item:contains(Apps1) i",
            run: "click",
        },
        {
            trigger: ".o_field_domain > div > div",
            run: "click",
        },
        {
            trigger: ".o_tree_editor_row:contains(New Rule) > a",
            run: "click",
        },
        {
            trigger: ".o_back_button > a",
            run: "click",
        },
        {
            trigger: ".o_facet_values:contains('Apps2')",
        },
        {
            trigger: ".o_kanban_header:contains(Account Charts)",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            trigger: ".o_favorite_menu .o-dropdown-item:contains(Apps1)",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:not(.o_kanban_ghost)",
            run() {
                if (queryAll(".o_kanban_record:not(.o_kanban_ghost)").length > 1) {
                    throw new Error("There should be only one visible card in the kanban view");
                }
            },
        },
        {
            trigger: ".o_favorite_menu .o-dropdown-item:contains(Apps1) i",
            run: "click",
        },
        {
            trigger: ".o_cp_action_menus .o-dropdown",
            run: "click",
        },
        {
            trigger: ".o_popover > .o-dropdown-item:contains(Delete)",
            run: "click",
        },
        {
            trigger: ".o_technical_modal button:contains(Delete)",
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            trigger: ".o_favorite_menu .o-dropdown-item:contains(Apps2)",
            run() {
                if (queryAll(".o_searchview_facet").length) {
                    throw new Error("There should not be any facet inside the search bar");
                }
                if (queryAll(".o_favorite_menu .o-dropdown-item:contains(Apps1)").length) {
                    throw new Error("The Apps1 filter should be deleted");
                }
            },
        },
    ],
});
