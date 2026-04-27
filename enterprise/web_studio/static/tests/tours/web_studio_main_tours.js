/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { randomString } from "@web_studio/utils";
import { assertEqual, stepNotInStudio } from "@web_studio/../tests/tours/tour_helpers";

const localStorage = browser.localStorage;
let createdAppString = null;
let createdMenuString = null;

registry.category("web_tour.tours").add("web_studio_main_and_rename", {
    url: "/odoo?debug=1",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: "click",
        },
        {
            // the next steps are here to create a new app
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: `edit ${(createdAppString = randomString(6))}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: `edit ${(createdMenuString = randomString(6))}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            // disable chatter in model configurator, we'll test adding it on later
            trigger: 'input[name="use_mail"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
        },
        {
            // toggle the home menu outside of studio and come back in studio
            trigger: ".o_web_studio_leave > a.btn",
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
            run: "click",
        },
        {
            trigger: `.o_web_client:not(.o_in_studio)` /* wait to be out of studio */,
        },
        {
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
            run: "click",
        },
        {
            trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            // open the app creator and leave it
            trigger: ".o_web_studio_new_app",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator",
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        {
            // go back to the previous app
            trigger: ".o_home_menu",
            run: "press Escape",
        },
        {
            trigger: `.o_web_client:not(.o_in_studio) .o_menu_brand:contains(${createdAppString})`,
        },
        {
            // this should open the previous app outside of studio
            // go back to the home menu
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
            run: "click",
        },
        {
            trigger: "input.o_search_hidden",
            // Open Command Palette
            run: `edit ${createdMenuString[0]}`,
        },
        {
            trigger: ".o_command_palette_search input",
            run: `edit /${createdMenuString}`,
        },
        {
            trigger: `.o_command.focused:contains(${createdAppString} / ${createdMenuString})`,
        },
        {
            // search results should have been updated
            trigger: ".o_command_palette",
            // Close the Command Palette
            run: "press Escape",
        },
        {
            // enter Studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_studio_home_menu",
        },
        {
            // edit an app
            trigger: `.o_app[data-menu-xmlid*="studio"]:contains(${createdAppString})`,
            run: function () {
                // We can't emulate a hover to display the edit icon
                const editIcon = this.anchor.querySelector(".o_web_studio_edit_icon");
                editIcon.style.visibility = "visible";
                editIcon.click();
            },
        },
        {
            // design the icon
            // TODO: we initially tested this (change an app icon) at the end but a
            // long-standing bug (KeyError: ir.ui.menu.display_name, caused by a registry
            // issue with multiple workers) on runbot prevent us from doing it. It thus have
            // been moved at the beginning of this test to avoid the registry to be reloaded
            // before the write on ir.ui.menu.
            trigger: ".o_web_studio_selector_background > button",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu .o_web_studio_selector_value",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn.btn-primary",
            run: "click",
        },
        {
            // click on the created app
            trigger: `.o_app[data-menu-xmlid*="studio"]:contains(${createdAppString})`,
            run: "click",
        },
        {
            // create a new menu
            trigger: ".o_main_navbar .o_web_edit_menu",
            run: "click",
        },
        {
            trigger: "footer.modal-footer .js_add_menu",
            run: "click",
        },
        {
            trigger: 'input[name="menuName"]',
            run: `edit ${(createdMenuString = randomString(6))}`,
        },
        {
            trigger: 'div.o_web_studio_menu_creator_model_choice input[value="existing"]',
            run: "click",
        },
        {
            trigger: "div.o_web_studio_menu_creator_model .o_record_selector input",
            run: "edit a",
        },
        {
            trigger:
                ".o_record_selector .o-autocomplete--dropdown-menu > li > a:not(:has(.fa-spin))",
            run: "click",
        },
        {
            trigger: ".o_record_selector :not(.o-autocomplete dropdown-menu)",
        },
        {
            trigger: ".o_web_studio_add_menu_modal button:contains(Confirm):not(.disabled)",
            run: "click",
        },
        {
            trigger: ":not(.o_inactive_modal) .o-web-studio-appmenu-editor",
        },
        {
            trigger: ".o-web-studio-appmenu-editor button:contains(Confirm):not(.disabled)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_menu",
        },
        {
            // check that the Studio menu is still there
            // switch to form view
            trigger: '.o_web_studio_views_icons > a[title="Form"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            // wait for the form editor to be rendered because the sidebar is the same
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            // add an new field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char",
            run: "drag_and_drop .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            trigger: '.o_web_studio_sidebar input[name="technical_name"]',
        },
        {
            // click on the field
            trigger: ".o_web_studio_form_view_editor .o_wrap_label:first label",
            // when it's there
            run: "click",
        },
        {
            // rename the label
            trigger: '.o_web_studio_sidebar input[name="string"]',
            run: "edit My Coucou Field && click .o_web_studio_sidebar",
        },
        {
            // verify that the field name has changed and change it
            trigger: '.o_web_studio_sidebar input[name="technical_name"]:value(my_coucou_field)',
            async run(helper) {
                await helper.edit("coucou");
                await helper.click(".o_web_studio_sidebar");
            },
            // the rename operation (/web_studio/rename_field + /web_studio/edit_view)
            // takes a while and sometimes reaches the default 10s timeout
            timeout: 20000,
        },
        {
            // click on "Add" tab
            trigger: ".o_web_studio_sidebar .o_web_studio_new",
            // the rename operation (/web_studio/rename_field + /web_studio/edit_view)
            // takes a while and sometimes reaches the default 10s timeout
            timeout: 20000,
            run: "click",
        },
        {
            // add a new field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char",
            run: "drag_and_drop .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            // rename the field with the same name
            trigger: '.o_web_studio_sidebar input[name="technical_name"]',
            run: "edit coucou && click body",
        },
        {
            // an alert dialog should be opened
            trigger: ".modal-footer > button:first",
            run: "click",
        },
        {
            // rename the label
            trigger: '.o_web_studio_sidebar input[name="string"]',
            run: "edit COUCOU && click body",
        },
        {
            // verify that the field name has changed (post-fixed by _1)
            trigger: '.o_web_studio_sidebar input[name="technical_name"]:value(coucou_1)',
            // the rename operation (/web_studio/rename_field + /web_studio/edit_view)
            // takes a while and sometimes reaches the default 10s timeout
            timeout: 20000,
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new",
            run: "click",
        },
        {
            // add a monetary field --> create a currency field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_monetary",
            run: "drag_and_drop (.o_inner_group:first .o_web_studio_hook:eq(1))",
        },
        {
            // verify that the monetary field is in the view
            trigger:
                '.o_web_studio_form_view_editor .o_wrap_label:eq(1) label:contains("New Monetary")',
        },
        {
            // switch the two first fields
            trigger: ".o_web_studio_form_view_editor .o_inner_group:first .o-draggable:eq(1)",
            run: "drag_and_drop .o_inner_group:first .o_web_studio_hook:first",
        },
        {
            // click on "Add" tab
            trigger:
                '.o_web_studio_form_view_editor .o_wrap_label:eq(0) label:contains("New Monetary")',
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new",
            run: "click",
        },
        {
            // verify that the fields have been switched
            trigger:
                '.o_web_studio_form_view_editor .o_wrap_label:eq(0) label:contains("New Monetary")',
        },
        {
            // add a m2m field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_many2many",
            run: "drag_and_drop .o_inner_group:first .o_web_studio_hook:first",
        },
        {
            // type something in the modal
            trigger:
                '.modal:not(.o_inactive_modal) [name="relation_id"] input.o-autocomplete--input',
            // we are sure "Activity" exists since studio depends on mail.
            //Also, it is determinisic and field names should not conflict too much.
            run: "fill mail.activity",
        },
        {
            // select Activity as model
            trigger:
                '.modal:not(.o_inactive_modal) [name="relation_id"] .o-autocomplete--dropdown-menu li a:not(:has(.fa-spin)):contains(Activity):not(:contains("Activity "))',
            run: "click",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) button:contains(Confirm):not(.disabled)",
            run: "click",
        },
        {
            // select the m2m to set its properties
            trigger: ".o_wrap_input:has(.o_field_many2many)",
            timeout: 15000, // creating M2M relations can take some time...
            run: "click",
        },
        {
            // change the `widget` attribute
            trigger: '.o_web_studio_sidebar [name="widget"] .o_select_menu_toggler_slot',
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu .o_select_menu_item_label:contains('(many2many_tags)')",
            run: "click",
        },
        {
            // use colors on the m2m tags
            trigger: '.o_web_studio_sidebar [name="color_field"]',
            run: "click",
        },
        {
            // add a statusbar
            trigger: ".o_web_studio_statusbar_hook",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_statusbar_status",
            run: "click",
        },
        {
            // verify that a default value has been set for the statusbar
            trigger:
                '.o_web_studio_sidebar [name="default_value"] .o_select_menu_toggler_slot:contains(First Status)',
        },
        {
            trigger: ".o_web_studio_views_icons a[aria-label=Form]",
            run: "click",
        },
        {
            // verify Chatter can be added after changing view to form
            trigger: ".o_web_studio_add_chatter",
        },
        {
            // edit action
            trigger: ".o_web_studio_menu .o_menu_sections li a:contains(Views)",
            run: "click",
        },
        {
            // edit form view
            trigger:
                ".o_web_studio_view_category .o_web_studio_thumbnail_item.o_web_studio_thumbnail_form",
            run: "click",
        },
        {
            // verify Chatter can be added after changing view to form
            trigger: ".o_web_studio_add_chatter",
        },
        {
            // switch in list view
            trigger: '.o_web_studio_menu .o_web_studio_views_icons a[title="List"]',
            run: "click",
        },
        {
            // wait for the list editor to be rendered because the sidebar is the same
            trigger: ".o_web_studio_list_view_editor",
        },
        {
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            // add an existing field (display_name)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_field_char:contains(COUCOU)",
            run: "drag_and_drop .o_web_studio_list_view_editor th.o_web_studio_hook:first",
        },
        {
            // verify that the field is correctly named
            trigger: '.o_web_studio_list_view_editor th:contains("COUCOU")',
        },
        {
            // leave Studio
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        {
            // come back to the home menu to check if the menu data have changed
            trigger: ".o_web_client:not(.o_in_studio)",
        },
        {
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
            run: "click",
        },
        {
            trigger: "input.o_search_hidden",
            // Open Command Palette
            run: `edit ${createdMenuString[0]}`,
        },
        {
            trigger: ".o_command_palette_search input",
            run: `edit /${createdMenuString}`,
        },
        {
            // search results should have been updated
            trigger: `.o_command.focused:contains(${createdAppString} / ${createdMenuString})`,
        },
        {
            trigger: ".o_command_palette",
            // Close the Command Palette
            run: `press Escape`,
        },
        {
            trigger: ".o_home_menu",
            // go back again to the app (using keyboard)
            run: `press Escape`,
        },
        {
            // wait to be back in the list view
            trigger: ".o_list_view",
        },
        {
            // re-open studio
            trigger: ".o_web_studio_navbar_item",
            run: "click",
        },
        {
            // modify the list view
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            //select field you want to sort and based on that sorting will be applied on List view
            trigger:
                '.o_web_studio_sidebar .o_web_studio_sidebar_select[name="sort_by"] .o_select_menu_toggler',
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item",
            run: "click",
        },
        {
            //change order of sorting, Select order and change it
            trigger:
                '.o_web_studio_sidebar .o_web_studio_sidebar_select[name="sort_order"] .o_select_menu_toggler',
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:nth-child(2)",
            run: "click",
        },
        {
            // edit action
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
            run: "click",
        },
        {
            // add a kanban
            trigger: ".o_web_studio_view_category .o_web_studio_thumbnail_kanban.disabled",
            run: "click",
        },
        {
            trigger: ".o_notebook .o_web_studio_new",
            run: "click",
        },
        {
            // add a menu
            trigger: ".o_web_studio_component.o_web_studio_field_menu",
            async run(helpers) {
                const hook = ".o_web_studio_hook[data-structures='t,kanban_colorpicker']";
                document.querySelector(hook).style.setProperty("transition", "none", "important");
                await helpers.drag_and_drop(hook);
            },
        },
        {
            // add an aside
            trigger: ".o_web_studio_component.o_web_studio_field_aside",
            async run(helpers) {
                const hook = ".o_web_studio_hook[data-structures='aside']";
                document.querySelector(hook).style.setProperty("transition", "none", "important");
                await helpers.drag_and_drop(hook);
            },
        },
        {
            trigger: ".o_kanban_record main",
            content: "card content has been wrapped in a <main> element",
        },
        {
            trigger: ".o_kanban_record aside",
        },
        {
            // add a colorpicker
            trigger: ".o_web_studio_component.o_web_studio_field_color_picker",
            async run(helpers) {
                const hook = ".o_web_studio_hook[data-structures='t,kanban_colorpicker']";
                document.querySelector(hook).style.setProperty("transition", "none", "important");
                await helpers.drag_and_drop(hook);
            },
        },
        {
            // select the menu for edition
            trigger: ".o_dropdown_kanban",
            run: "click",
        },
        {
            // select the colorpicker for edition
            trigger: "button.o_web_studio_field_color_picker:contains(Edit Color Picker)",
            run: "click",
        },
        {
            trigger: ".o_notebook_content h3:contains(Field)",
            content: "sidebar is editing the color field",
        },
        {
            trigger: ".o_notebook .o_web_studio_view",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_property_highlight_color .o_select_menu_toggler:contains(Card color)",
        },
        {
            // edit action
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
            run: "click",
        },
        {
            // check that the kanban view is now active
            trigger: ".o_web_studio_view_category .o_web_studio_thumbnail_kanban:not(.disabled)",
        },
        {
            // add an activity view
            trigger: ".o_web_studio_view_category .o_web_studio_thumbnail_activity.disabled",
            run: "click",
        },
        {
            trigger: ".o_activity_view",
        },
        {
            // edit action
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
            timeout: 20000, // activating a view takes a while and sometimes reaches the default 10s timeout
            run: "click",
        },
        {
            // add a graph view
            trigger: ".o_web_studio_view_category .o_web_studio_thumbnail_graph.disabled",
            run: "click",
        },
        {
            trigger: ".o_graph_renderer",
        },
        {
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
            run: "click",
        },
        {
            trigger: ".o_web_studio_views",
        },
        {
            run: "click",
            // edit the search view
            trigger:
                ".o_web_studio_view_category .o_web_studio_thumbnail_item.o_web_studio_thumbnail_search",
        },
        {
            trigger: ".o_web_studio_search_view_editor",
        },
        {
            run: "click",
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
        },
        {
            // export all modifications
            trigger: ".o_web_studio_export",
            run: "click",
        },
        {
            content: "check that export feature is blazing fast",
            trigger: ".modal .modal-footer button:contains(export)",
            run: "click",
        },
        {
            content: "close modal",
            trigger: ".modal .modal-footer button:contains(cancel)",
            run: "click",
        },
        {
            // click on the created app
            trigger: '.o_app[data-menu-xmlid*="studio"]:last',
            run: "click",
        },
        {
            // switch to form view
            trigger: '.o_web_studio_views_icons > a[title="Form"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            // click on the view tab
            trigger: ".o_web_studio_view",
            run: "click",
        },
        {
            // click on the restore default view button
            trigger: ".o_web_studio_restore",
            run: "click",
        },
        {
            // click on the ok button
            trigger: ".modal-footer .btn.btn-primary",
            run: "click",
        },
        {
            // checks that the field doesn't exist anymore
            trigger: ".o_web_studio_form_view_editor:not(:has(.o_form_label))",
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        ...stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_hide_fields_tour", {
    url: "/odoo/action-studio?mode=home_menu&debug=1",
    steps: () => [
        {
            trigger: ".o_web_studio_new_app",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_app_creator_name
        > input`,
            run: `edit ${randomString(6)}`,
        },
        {
            // make another interaction to show "next" button
            trigger: `
        .o_web_studio_selectors
        .o_web_studio_selector_icon > button`,
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_menu_creator
        > input`,
            run: `edit ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            // check that the Studio menu is still there
            trigger: ".o_web_studio_menu",
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
            run: "click",
        },
        {
            trigger: ".oe_title input",
            run: "edit Test",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_menu",
        },
        {
            run: "click",
            trigger: `
        .o_web_studio_views_icons
        > a[title="List"]`,
        },
        {
            // wait for the list editor to be rendered because the sidebar is the same
            trigger: ".o_web_studio_list_view_editor",
        },
        {
            trigger: ".o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_sidebar
        .o_web_studio_existing_fields
        .o_web_studio_component:has(.o_web_studio_component_description:contains(display_name))`,
            run: "drag_and_drop .o_web_studio_list_view_editor .o_web_studio_hook",
        },
        {
            trigger: `
        .o_list_table
        th[data-name="display_name"]`,
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_sidebar
        [name="optional"] .o_select_menu_toggler`,
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu .o_select_menu_item:contains(Hide by default)",
            run: "click",
        },
        {
            trigger: '.o_list_table:not(:has(th[data-name="display_name"]))',
        },
        {
            trigger: `
        .o_web_studio_sidebar
        .o_web_studio_view`,
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_sidebar_checkbox
        input#show_invisible`,
            run: "click",
        },
        {
            trigger: `
        .o_list_table
        th[data-name="display_name"].o_web_studio_show_invisible`,
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        ...stepNotInStudio(".o_list_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_model_option_value_tour", {
    url: "/odoo/action-studio?mode=home_menu&debug=tests",
    steps: () => [
        {
            trigger: ".o_web_studio_new_app",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_app_creator_name
        > input`,
            run: `edit ${randomString(6)}`,
        },
        {
            trigger: `
        .o_web_studio_selectors
        .o_web_studio_selector_icon > button`,
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_menu_creator
        > input`,
            run: `edit ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            // check monetary value in model configurator
            trigger: 'input[name="use_value"]',
            run: "click",
        },
        {
            // check lines value in model configurator
            trigger: 'input[name="lines"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            trigger: '.o_web_studio_menu .o_web_studio_views_icons > a[title="Graph"]',
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
            run: "click",
        },
        {
            // wait for the graph editor to be rendered and also check for sample data
            trigger: ".o_view_sample_data .o_graph_renderer",
        },
        {
            trigger: '.o_web_studio_menu .o_web_studio_views_icons a[title="Pivot"]',
            run: "click",
        },
        {
            // wait for the pivot editor to be rendered and also check for sample data
            trigger: ".o_pivot_view .o_view_sample_data .o_view_nocontent_empty_folder",
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        ...stepNotInStudio(".o_pivot_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_new_submenu_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: "body.o_in_studio",
        },
        {
            // click on the created app
            trigger: '.o_app[data-menu-xmlid*="studio"]:first',
            run: "click",
        },
        {
            // create a new menu
            trigger: ".o-studio--menu .o_web_create_new_model",
            run: "click",
        },
        {
            trigger: "input[name=model_name]",
            run: `edit second menu ${randomString(6)}`,
        },
        {
            trigger: ".confirm_button",
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            // leave studio
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        {
            trigger: ".o_web_client:not(.o_in_studio)",
        },
        {
            // open studio again to check the new menu can be edited
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            // check we are back in studio
            trigger: ".o_in_studio",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_new_report_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: "body.o_in_studio",
        },
        {
            // click on the created app
            trigger: '.o_app[data-menu-xmlid*="studio"]:first',
            run: "click",
        },
        {
            // edit reports
            trigger: ".o_web_studio_menu li a:contains(Reports)",
            run: "click",
        },
        {
            // create a new report
            trigger: ".o_control_panel .o-kanban-button-new",
            run: "click",
        },
        {
            // select external layout
            trigger: '.o_web_studio_report_layout_dialog div[data-layout="web.external_layout"]',
            run: "click",
        },
        {
            // edit report name
            trigger: '.o_web_studio_sidebar input[id="name"]',
            run: "edit My Awesome Report && click body",
        },
        {
            // add a new group on the node
            trigger: '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] input',
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu li:contains(Access Rights)",
            run: "click",
        },
        {
            // wait for the group to appear
            trigger:
                '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] .o_tag_badge_text:contains(Access Rights)',
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable div.page div",
            run() {
                this.anchor.ownerDocument.getSelection().setPosition(this.anchor);
                assertEqual(
                    this.anchor.outerHTML,
                    `<div class="oe_structure o-paragraph" o-diff-key="3"><br></div>`
                );
            },
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable div.page div",
            run() {
                assertEqual(this.anchor.classList.contains("o-we-hint"), true);
            },
        },
        {
            trigger:
                ".o-web-studio-report-editor-wysiwyg :iframe .odoo-editor-editable div.page div",
            run: "editor some new text",
        },
        {
            trigger: ".o_web_studio_menu .o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            // The report has been saved
            trigger: ".o_web_studio_menu .o-web-studio-save-report:not(.btn-primary)",
        },
        {
            trigger: ".o_web_studio_breadcrumb .o_back_button:contains(Reports)",
            run: "click",
        },
        {
            content: "open the dropdown",
            trigger: ".o_kanban_record:contains(My Awesome Report) .dropdown-toggle:not(:visible)",
            run: "click",
        },
        {
            // duplicate the report
            trigger: ".dropdown-menu a:contains(Duplicate)",
            run: "click",
        },
        {
            // open the duplicate report
            trigger: ".o_kanban_record:contains(My Awesome Report copy(1))",
            run: "click",
        },
        {
            // switch to 'Report' tab
            trigger: ".o_web_studio_sidebar input[id='name']",
            run() {
                assertEqual(this.anchor.value, "My Awesome Report copy(1)");
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg :iframe div.page div",
            run() {
                assertEqual(this.anchor.textContent, "some new text");
            },
        },
        {
            trigger:
                '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] .o_tag_badge_text:contains(Access Rights)',
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        ...stepNotInStudio(),
    ],
});

registry.category("web_tour.tours").add("web_studio_new_report_basic_layout_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: "body.o_in_studio",
        },
        {
            // click on the created app
            trigger: '.o_app[data-menu-xmlid*="studio"]:first',
            run: "click",
        },
        {
            // edit reports
            trigger: ".o_web_studio_menu li a:contains(Reports)",
            run: "click",
        },
        {
            // create a new report
            trigger: ".o_control_panel .o-kanban-button-new",
            run: "click",
        },
        {
            // select basic layout
            trigger: '.o_web_studio_report_layout_dialog div[data-layout="web.basic_layout"]',
            run: "click",
        },
        {
            // edit report name
            trigger: '.o_web_studio_sidebar input[id="name"]',
            run: "edit My Awesome basic layout Report && click body",
        },
        {
            // add a new group on the node
            trigger: '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] input',
            run: "click",
        },
        {
            trigger: ".o-autocomplete--dropdown-menu li:contains(Access Rights)",
            run: "click",
        },
        {
            // wait for the group to appear
            trigger:
                '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] .o_tag_badge_text:contains(Access Rights)',
        },
        {
            trigger: ".o_web_studio_menu .o-web-studio-save-report.btn-primary",
            run: "click",
        },
        {
            // The report has been saved
            trigger: ".o_web_studio_menu .o-web-studio-save-report:not(.btn-primary)",
        },
        {
            // leave the report
            trigger: ".o_web_studio_breadcrumb .o_back_button:contains(Reports)",
            run: "click",
        },
        {
            content: "open the dropdown",
            trigger: ".o_kanban_record:contains(My Awesome basic layout Report)",
            run: "hover && click .o_kanban_record:contains(My Awesome basic layout Report) .dropdown-toggle",
        },
        {
            // duplicate the report
            trigger: ".dropdown-menu .dropdown-item:contains(Duplicate)",
            run: "click",
        },
        {
            // open the duplicate report
            trigger: ".o_kanban_record:contains(My Awesome basic layout Report copy(1))",
            run: "click",
        },
        {
            trigger: '.o_web_studio_sidebar input[id="name"]',
            run() {
                assertEqual(this.anchor.value, "My Awesome basic layout Report copy(1)");
            },
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        ...stepNotInStudio(),
    ],
});

registry.category("web_tour.tours").add("web_studio_approval_tour", {
    url: "/odoo?debug=1",
    steps: () => [
        {
            // go to Apps menu
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: "click",
        },
        {
            trigger: ".o_cp_switch_buttons",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            // switch to form view editor
            trigger: '.o_web_studio_views_icons > a[title="Form"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar #show_invisible",
            run: "click",
        },
        {
            content: "click on first button it finds that has a node id",
            trigger:
                ".o_web_studio_form_view_editor button[name='button_immediate_upgrade'].o-web-studio-editor--element-clickable",
            run: "click",
        },
        {
            // enable approvals for the button
            trigger: '.o_web_studio_sidebar_approval [name="create_approval_rule"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            // add approval rule
            trigger: '.o_web_studio_sidebar_approval [name="create_approval_rule"]',
            run: "click",
        },
        {
            // set approval message
            trigger: '.o_web_studio_sidebar_approval input[name*="approval_message"]',
            run: "edit nope",
        },
        {
            trigger: ".o_studio_sidebar_approval_rule:eq(1)",
        },
        {
            // set domain on first rule
            trigger: ".o_web_studio_sidebar_approval .o_approval_domain",
            run: "click",
        },
        {
            // set stupid domain that is always truthy
            trigger: ".o_domain_selector_debug_container textarea",
            run: function () {
                this.anchor.focus();
                this.anchor.value = '[["id", "!=", False]]';
                this.anchor.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            // save domain and close modal
            trigger: " .modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            // add second approval rule when the first is set
            trigger: '.o_web_studio_sidebar_approval [name="create_approval_rule"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            // enable 'force different users' for one rule (doesn't matter which)
            trigger: '.o_web_studio_sidebar label[for*="exclusive_user"]',
            run: "click",
        },
        {
            // switch to kanban view editor
            trigger: '.o_web_studio_views_icons > a[title="Kanban"]',
            run: "click",
        },
        {
            // leave studio
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        {
            trigger: ".o_web_client:not(.o_in_studio)",
        },
        {
            // TODO: add breacrumb to access multi-record view when closing studio and close studio from form instead of from kanban
            // trigger: ".o_breadcrumb .o_back_button",
            trigger: "body",
        },
        {
            trigger: ".o_searchview_dropdown_toggler",
            run: "click",
        },
        {
            trigger: ".o-dropdown-item:contains(Installed)",
            run: "click",
        },
        {
            trigger: ".o_searchview_input",
            run: "edit web_studio",
        },
        {
            trigger: ".o_menu_item.dropdown-item:contains(Module)",
            run: "click",
        },
        {
            trigger: ".o_kanban_record:not(.o_kanban_ghost):only",
        },
        {
            content:
                "open first record (should be the one that was used, so the button should be there)",
            trigger:
                ".o_kanban_view .o_kanban_record:not(.o_kanban_ghost):not(:has(button[name='button_immediate_install'])) .o_dropdown_kanban .dropdown-toggle",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu .dropdown-item",
            run: "click",
        },
        {
            // try to do the action
            trigger: "button[name='button_immediate_upgrade']",
            run: "click",
        },
        {
            // there should be a warning
            trigger: ".o_notification_bar.bg-warning",
            run: "click",
        },
        {
            trigger: ".breadcrumb .o_back_button",
            run: "click",
        },
        {
            trigger: "body .o_modules_kanban",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_custom_field_tour", {
    url: "/odoo",
    steps: () => [
        {
            // go to Apps menu
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: "click",
        },
        {
            // click on the list view
            trigger: ".o_switch_view.o_list",
            run: "click",
        },
        {
            // click on optional column dropdown
            trigger: ".o_optional_columns_dropdown_toggle",
            run: "click",
        },
        {
            // click on add custom field
            trigger: ".dropdown-item-studio",
            run: "click",
        },
        {
            trigger: ".o_web_client.o_in_studio",
        },
        {
            // go to home menu
            trigger: ".o_menu_toggle",
            run: "click",
        },
        {
            //leave studio
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        {
            trigger: ".o_web_client:not(.o_in_studio)",
        },
        {
            // studio left.
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_local_storage_tour", {
    url: "/odoo",
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: function () {
                localStorage.setItem("openStudioOnReload", "main");
                window.location.reload();
            },
            expectUnloadPage: true,
        },
        {
            trigger: ".o_web_client.o_in_studio",
        },
        {
            // should be directly in studio mode
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: "click",
        },
        {
            trigger: ".o_menu_toggle",
            run: "click",
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
            run: "click",
        },
        {
            trigger: ".o_web_client:not(.o_in_studio)",
        },
        {
            // studio left.
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: function () {
                window.location.reload();
            },
            expectUnloadPage: true,
        },
        {
            trigger: ".o_web_client:not(.o_in_studio)",
        },
        {
            // studio left after refresh.
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_custom_background_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "class for custom background must be enabled (outside studio)",
            trigger: ".o_home_menu_background_custom.o_home_menu_background:not(.o_in_studio)",
            run: () => null,
        },
        {
            content: "opening studio",
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            content: "class for custom background must be enabled (in studio)",
            trigger: ".o_home_menu_background_custom.o_home_menu_background.o_in_studio",
            run: () => null,
        },
        {
            content: "reset the background",
            trigger: ".o_web_studio_reset_default_background",
            run: "click",
        },
        {
            content: "validate the reset of the background",
            trigger: ".modal-dialog .btn-primary",
            run: "click",
            expectUnloadPage: true,
        },
        {
            content: "class for custom background must be disabled (inside studio)",
            trigger: ".o_home_menu_background.o_in_studio:not(.o_home_menu_background_custom)",
            run: () => null,
        },
        {
            content: "leaving studio",
            trigger: ".o_web_studio_leave a",
            run: "click",
        },
        {
            content: "class for custom background must be disabled (outside studio)",
            trigger: ".o_home_menu_background:not(.o_in_studio.o_home_menu_background_custom)",
            run: () => null,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_create_app_with_pipeline_and_user_assignment", {
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: "click",
        },
        {
            // the next steps are here to create a new app
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: `edit ${(createdAppString = randomString(6))}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: `edit ${(createdAppString = randomString(6))}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            trigger: "input#use_stages",
            run: "click",
        },
        {
            trigger: "input#use_responsible",
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editor .o_menu_sections a:contains(Views)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_thumbnail_item.o_web_studio_thumbnail_kanban",
            run: "click",
        },
        {
            trigger: ".o_web_studio_kanban_view_editor",
        },
        {
            trigger: ".o_avatar.o_m2o_avatar",
            run() {
                const avatarImg = document.querySelector(".o_avatar.o_m2o_avatar a");
                if (!avatarImg.getAttribute("title") === "Assign") {
                    throw new Error(
                        "It should be possible to assign a record, when no one is currently selected"
                    );
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_alter_field_existing_in_multiple_views_tour", {
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item button",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: "click",
        },
        {
            // the next steps are here to create a new app
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: `edit ${(createdAppString = randomString(6))}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: `edit ${createdAppString}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar",
        },
        {
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
            timeout: 60000,
            run: "click",
        },
        {
            // add an existing field (the one we created)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(2) .o_web_studio_field_many2many:contains(Followers (Partners))",
            run: "drag_and_drop .o_inner_group:first .o_web_studio_hook:first",
        },
        {
            trigger: ".o_web_studio_new ",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_many2many",
            run: "drag_and_drop div.o_web_studio_hook:last",
        },
        {
            trigger: ".modal-body",
        },
        {
            trigger: '.modal:not(.o_inactive_modal) [name="relation_id"] input',
            run: `edit ${createdAppString}`,
        },
        {
            // select the first model
            trigger:
                ".modal:not(.o_inactive_modal) .o-autocomplete--dropdown-menu > li > a:not(:has(.fa-spin))",
            run: "click",
        },
        {
            trigger: "button:contains(Confirm)",
            run: "click",
        },
        {
            // edit list view
            trigger: ".o_web_studio_editX2Many",
            run: "click",
        },
        {
            // wait for list view to be loaded
            trigger: ".o_web_studio_list_view_editor",
        },
        {
            // go to view
            trigger: ".o_web_studio_view ",
            run: "click",
        },
        {
            // show invisible elements
            trigger: 'label[for="show_invisible"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_new ",
            run: "click",
        },
        {
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            // add an existing field (the one we created)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_many2many:contains(Followers (Partners))",
            run: "drag_and_drop .o_web_studio_list_view_editor th.o_web_studio_hook:first",
        },
        {
            // select field
            trigger: "th[data-name='message_partner_ids']",
            run: "click",
        },
        {
            // make it invisible
            trigger: "#invisible",
            run: "click",
        },
        {
            trigger: ".o_web_studio_snackbar .fa.fa-check",
        },
        {
            // check if the invisible option is checked
            trigger: "#invisible:checked",
        },
    ],
});

const buttonToogleStudio = {
    trigger: `button[title="Toggle Studio"]`,
    run: "click",
};
const addActionButtonModalSteps = (
    ActionLabel = "web_studio_new_button_action_name",
    ActionName = "Privacy Lookup"
) => [
    {
        trigger: ".o-web-studio-editor--add-button-action",
        run: "click",
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action input#set_label",
        run: `edit ${ActionLabel}`,
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action input#set_button_type_to_action",
        run: "click",
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action .o_record_selector input",
        run: `edit ${ActionName}`,
    },
    {
        trigger: `.o-web-studio-editor--modal-add-action .o-autocomplete--dropdown-menu li a:not(:has(.fa-spin)):contains(${ActionName})`,
        run: "click",
    },
    {
        trigger: "footer button.o-web-studio-editor--add-button-confirm",
        run: "click",
    },
];

const addMethodButtonModalSteps = () => [
    {
        trigger: ".o-web-studio-editor--add-button-action",
        run: "click",
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action input#set_label",
        run: `edit test`,
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action input#set_button_type_to_object",
        run: "click",
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action  input#set_method",
        run: `edit demo && click body`,
    },
];

registry.category("web_tour.tours").add("web_studio_check_method_in_model", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        buttonToogleStudio,
        ...addMethodButtonModalSteps(),
        {
            trigger: "div.text-danger",
            run() {
                const div_error = document.querySelector("div.text-danger");
                assertEqual(
                    div_error.innerHTML,
                    "The method demo does not exist on the model res.partner()."
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_action_button_in_form_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        buttonToogleStudio,
        ...addActionButtonModalSteps(),
        {
            trigger: ".o_web_studio_leave a",
            run: "click",
        },
        ...stepNotInStudio(".o_form_view"),
    ],
});

registry
    .category("web_tour.tours")
    .add("web_studio_test_create_second_action_button_in_form_view", {
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
                run: "click",
            },
            {
                trigger: ".o_form_view .o_form_editable",
                run: "click",
            },
            buttonToogleStudio,
            ...addActionButtonModalSteps("web_studio_other_button_action_name", "Download (vCard)"),
            {
                trigger: ".o_web_studio_leave a",
                run: "click",
            },
            ...stepNotInStudio(".o_form_view"),
        ],
    });

registry.category("web_tour.tours").add("web_studio_test_create_action_button_in_list_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        buttonToogleStudio,
        {
            trigger: ".o_web_studio_views_icons a[aria-label='List']",
            run: "click",
        },
        {
            trigger: ".o_optional_columns_dropdown button",
            run: "click",
        },
        ...addActionButtonModalSteps(),
        {
            trigger: ".o_web_studio_leave a",
            run: "click",
        },
        ...stepNotInStudio(".o_list_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_remove_action_button_in_form_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        buttonToogleStudio,
        {
            trigger: 'button[studioxpath="/form[1]/header[1]/button[1]"]',
            run: "click",
        },
        {
            trigger: "button.o_web_studio_remove",
            run: "click",
        },
        {
            trigger: "footer.modal-footer>button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_leave a",
            run: "click",
        },
        ...stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_remove_action_button_in_list_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        buttonToogleStudio,
        {
            trigger: ".o_web_studio_views_icons a[aria-label='List']",
            run: "click",
        },
        {
            trigger: ".o_optional_columns_dropdown button",
            run: "click",
        },
        {
            trigger: 'button[studioxpath="/list[1]/header[1]/button[1]"]',
            run: "click",
        },
        {
            trigger: "button.o_web_studio_remove",
            run: "click",
        },
        {
            trigger: "footer.modal-footer>button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_leave a",
            run: "click",
        },
        ...stepNotInStudio(".o_list_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_create", {
    url: "/odoo?debug=1",
    steps: () => [
        // This tour drag&drop a monetary field and verify that a currency is created
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
            run: "click",
        },
        // drag&drop a monetary and verify that the currency is in the view
        {
            // add a new monetary field
            trigger: ".o_web_studio_sidebar .o_web_studio_field_monetary",
            run: "drag_and_drop .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            // verify that the currency is set
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field .text-start",
            run() {
                assertEqual(this.anchor.textContent, "Currency (x_studio_currency_id)");
            },
        },
        {
            // currency field is in the view
            trigger: ".o_web_studio_view_renderer div[data-field-name='x_studio_currency_id']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_properties.active",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_change_currency_name", {
    url: "/odoo?debug=1",
    steps: () => [
        // Changing currency name also change the currency name in the monetary currency selection
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
            run: "click",
        },
        {
            // currency field is in the view and click on it
            trigger: ".o_web_studio_view_renderer [data-field-name='x_studio_currency_test']",
            run: "click",
        },
        {
            // change the currency name
            trigger: "input[name='string']",
            run: "edit NewCurrency && click body",
        },
        {
            // click on monetary
            trigger: "div[data-field-name^='x_studio_monetary_test']",
            run: "click",
        },
        {
            // verify that the currency name changed in the monetary field
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field .text-start",
            run() {
                assertEqual(this.anchor.textContent, "NewCurrency (x_studio_currency_test)");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_related_monetary_creation", {
    url: "/odoo?debug=1",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
            run: "click",
        },
        {
            // add a new related field
            trigger: ".o_web_studio_sidebar .o_web_studio_field_related",
            run: "drag_and_drop .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            trigger: ".o_model_field_selector_value",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit X Test",
        },
        {
            run: "click",
            trigger:
                ".o_model_field_selector_popover_item[data-name='x_test'] .o_model_field_selector_popover_item_relation",
        },
        {
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit X Studio Monetary Test",
        },
        {
            run: "click",
            trigger:
                ".o_model_field_selector_popover_item[data-name='x_studio_monetary_test'] button",
        },
        {
            trigger: ".modal-footer button.btn-primary",
            run: "click",
        },
        {
            // The related monetary is created
            trigger: ".o_web_studio_view_renderer .o_form_label:contains('New Related Field')",
            run: "click",
        },
        {
            // The currency is created
            trigger: ".o_web_studio_view_renderer [data-field-name='x_studio_currency_id']",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_change_currency_field", {
    url: "/odoo",
    steps: () => [
        // Change currency and verify that the view take the changes into account (the dollar appears)
        {
            // open the custom app form view
            trigger: "a[data-menu-xmlid='web_studio.studio_app_menu']",
            run: "click",
        },
        {
            // fill the required char input
            trigger: ".o_field_char input",
            run: "edit title",
        },
        {
            // fill the new currency (many2one) input #1
            trigger: "div [name='x_studio_currency_test2'] input",
            run: "edit USD",
        },
        {
            // add a new currency field step #2
            trigger: '.ui-menu-item a:contains("USD")',
            run: "click",
        },
        {
            // save the view form
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_saved",
        },
        {
            // open studio with the record
            trigger: ".o_main_navbar .o_web_studio_navbar_item button",
            run: "click",
        },
        {
            // check that there is no currency symbol in renderer
            trigger: "div[name='x_studio_monetary_test'] span",
            run() {
                assertEqual(this.anchor.textContent, "0.00");
            },
        },
        {
            // click on the monetary field
            trigger: "div[data-field-name='x_studio_monetary_test']",
            run: "click",
        },
        {
            // change the currency_field in the monetary
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field button",
            run: "click",
        },
        {
            // click on the second currency, which is "X Studio Currency Test2"
            trigger: ".o-dropdown--menu .o_select_menu_item:nth-child(2)",
            run: "click",
        },
        {
            //wait until the currency has been set (also test the reactivity)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property_currency_field span.text-start:contains('X Studio Currency Test2')",
        },
        {
            // by changing the currency, we should have a $ symbol in the renderer
            trigger: "div[name^='x_studio_monetary'] span",
            run() {
                assertEqual(this.anchor.textContent, "$ 0.00");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_change_currency_not_in_view", {
    url: "/odoo",
    steps: () => [
        // Change a currency that is not present in the view insert it in the view
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
            run: "click",
        },
        {
            // click on the monetary field
            trigger: "div[data-field-name='x_studio_monetary_test']",
            run: "click",
        },
        {
            // change the currency_field in the monetary
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field button",
            run: "click",
        },
        {
            // click on the second currency, which is "X Studio Currency Test2"
            trigger: ".o-dropdown--menu .o_select_menu_item:nth-child(2)",
            run: "click",
        },
        {
            // wait until the currency has been set
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property_currency_field span.text-start:contains('X Studio Currency Test2')",
        },
        {
            // go to view tab
            trigger: ".o_web_studio_view",
            run: "click",
        },
        {
            // currency field is in the view and click on it
            trigger: ".o_web_studio_view_renderer div[data-field-name='x_studio_currency_test2']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_properties.active",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_add_existing_monetary", {
    url: "/odoo?debug=1",
    steps: () => [
        // Add an existing monetary trough the "existing fields" and verify that the currency
        // is added to the view
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
            run: "click",
        },
        {
            // click on "existing fields"
            trigger: ".o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            // add the existing monetary field
            trigger: ".o_web_studio_existing_fields_section .o_web_studio_field_monetary",
            run: "drag_and_drop .o_form_renderer .o_web_studio_hook",
        },
        {
            // monetary exist and click on monetary
            trigger: "div[data-field-name='x_studio_monetary_test']",
            run: "click",
        },
        {
            // verify that the currency name changed in the monetary field
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field .text-start",
            run() {
                assertEqual(
                    this.anchor.textContent,
                    "X Studio Currency Test (x_studio_currency_test)"
                );
            },
        },
        {
            // currency field is in the view
            trigger: "div[data-field-name='x_studio_currency_test']",
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("web_studio_monetary_create_monetary_with_existing_currency", {
        url: "/odoo?debug=1",
        steps: () => [
            // Add a new monetary field, since a currency already exists, it should take it instead
            // of creating a new one
            {
                trigger: ".o_home_menu_background",
            },
            {
                // open studio
                trigger: ".o_main_navbar .o_web_studio_navbar_item",
                run: "click",
            },
            {
                trigger: ".o_web_studio_new_app",
            },
            {
                trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
                run: "click",
            },
            {
                // go to Add tab
                trigger: ".o_web_studio_new",
                run: "click",
            },
            {
                // add a new monetary field
                trigger: ".o_web_studio_sidebar .o_web_studio_field_monetary",
                async run(helpers) {
                    await helpers.drag_and_drop(
                        `.o_web_studio_form_view_editor .o_inner_group .o_web_studio_hook:eq(1)`,
                        {
                            position: {
                                bottom: 0,
                            },
                            relative: true,
                        }
                    );
                },
            },
            {
                // there is only one occurence of the currency field in the view
                trigger: ".o_form_renderer div[data-field-name^='x_studio_monetary']",
                run() {
                    const o2mNumber = document.querySelectorAll("div.o_field_many2one");
                    assertEqual(o2mNumber.length, 1);
                },
            },
        ],
    });

registry.category("web_tour.tours").add("web_studio_add_field_into_empty_group_by", {
    url: "/odoo?debug=1",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: `edit ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: `edit ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
            run: "click",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            trigger: ".o_web_studio_views_icons a:last",
            run: "click",
        },
        {
            trigger: `
        .o_web_studio_sidebar
        .o_web_studio_existing_fields
        .o_web_studio_component:has(.o_web_studio_component_description:contains(create_date))`,
            run: "drag_and_drop .o-web-studio-search--groupbys .o_web_studio_hook",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_action_in_form_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        buttonToogleStudio,
        ...addActionButtonModalSteps("web_studio_custom_action_name", "Test Action"),
        {
            trigger: ".o_web_studio_leave a",
            run: "click",
        },
        ...stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_remove_action_in_form_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        buttonToogleStudio,
        {
            trigger: 'button[studioxpath="/form[1]/header[1]/button[1]"]',
            run: "click",
        },
        {
            trigger: "button.o_web_studio_remove",
            run: "click",
        },
        {
            trigger: "footer.modal-footer>button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_leave a",
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_cohort_measure_values", {
    url: "/web?debug=1",
    steps: () => [
        {
            trigger: ".o_home_menu_background",
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            run: "click",
        },
        {
            trigger: "body.o_in_studio",
        },
        {
            // click on the created app
            trigger: ".o_app[data-menu-xmlid*='studio']:first",
            run: "click",
        },
        {
            trigger: ".o_web_studio_menu .o_menu_sections a:contains('Views')",
            run: "click",
        },
        {
            // open cohort view
            trigger: ".o_web_studio_view_category .o_web_studio_thumbnail_cohort.disabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_property_measure .o_select_menu_toggler",
            run: "click",
        },
        {
            trigger: ".dropdown-menu .dropdown-item:contains('color')",
            run: "click",
        },
    ],
});
