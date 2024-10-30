import { queryAll } from "@odoo/hoot-dom";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_favorite_management", {
    url: "/odoo?debug=assets",
    steps: () => [
        {
            trigger: ".o_app[data-menu-xmlid='base\\.menu_management']",
            run: "click",
        },
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
            trigger: ".o_kanban_header:contains(Account Charts):contains(112)",
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
            trigger: ".o_debug_manager .o-dropdown",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item:contains(Filters) > span",
            run: "click",
        },
        {
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='name'] > .o_input",
            run: "edit Apps3",
        },
        {
            trigger: ".o_field_widget[name='user_id'] .o-autocomplete--input",
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains(Mitchell Admin) > a",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='model_id'] > .o_input",
            run: "selectByLabel /^Module$/",
        },
        {
            trigger: ".o_field_widget[name='action_id'] .o-autocomplete--input",
            run: "edit apps",
        },
        {
            trigger: ".o-autocomplete--dropdown-item:contains(Apps) > a",
            run: "click",
        },
        {
            trigger: ".o_tree_editor_row:contains(New Rule) > a",
            run: "click",
        },
        {
            trigger: ".o_breadcrumb li:contains(Apps) > a",
            run: "click",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            trigger: ".o_searchview",
            run() {
                if (queryAll(".o_searchview_facet").length) {
                    throw new Error("There should be no facet in the search view");
                }
            },
        },
        {
            trigger: ".o_favorite_menu .o-dropdown-item:contains(Apps3) span",
            run: "click",
        },
        {
            trigger: ".o_searchview_facet",
        },
        {
            trigger: ".o_kanban_record:not(.o_kanban_ghost)",
            run() {
                if (queryAll(".o_kanban_record:not(.o_kanban_ghost)").length > 1) {
                    throw new Error("There should be only one visible card in the kanban view");
                }
            },
            pause: true,
        },
    ],
});
