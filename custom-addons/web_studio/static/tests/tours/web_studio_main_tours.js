/** @odoo-module */

import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { randomString } from "@web_studio/utils";
import {
    assertEqual,
    stepNextTick,
    stepNotInStudio,
} from "@web_studio/../tests/tours/tour_helpers";

const localStorage = browser.localStorage;
let createdAppString = null;
let createdMenuString = null;

registry.category("web_tour.tours").add("web_studio_main_and_rename", {
    url: "/web?debug=1",
    test: true,
    steps: () => [
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            // the next steps are here to create a new app
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: "text " + (createdAppString = randomString(6)),
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: "text " + (createdMenuString = randomString(6)),
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            // disable chatter in model configurator, we'll test adding it on later
            trigger: 'input[name="use_mail"]',
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            // toggle the home menu outside of studio and come back in studio
            extra_trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
            trigger: ".o_web_studio_leave > a.btn",
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
        },
        {
            extra_trigger: `.o_web_client:not(.o_in_studio)` /* wait to be out of studio */,
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
        },
        {
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            // open the app creator and leave it
            trigger: ".o_web_studio_new_app",
        },
        {
            extra_trigger: ".o_web_studio_app_creator",
            trigger: ".o_web_studio_leave > a.btn",
        },
        {
            // go back to the previous app
            trigger: ".o_home_menu",
            run: () => {
                window.dispatchEvent(
                    new KeyboardEvent("keydown", {
                        bubbles: true,
                        key: "Escape",
                    })
                );
            },
        },
        {
            // this should open the previous app outside of studio
            extra_trigger: `.o_web_client:not(.o_in_studio) .o_menu_brand:contains(${createdAppString})`,
            // go back to the home menu
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
        },
        {
            trigger: "input.o_search_hidden",
            // Open Command Palette
            run: "text " + createdMenuString[0],
        },
        {
            trigger: ".o_command_palette_search input",
            run: "text " + "/" + createdMenuString,
        },
        {
            // search results should have been updated
            extra_trigger: `.o_command.focused:contains(${createdAppString} / ${createdMenuString})`,
            trigger: ".o_command_palette",
            // Close the Command Palette
            run: () => {
                window.dispatchEvent(
                    new KeyboardEvent("keydown", {
                        key: "Escape",
                    })
                );
            },
        },
        {
            // enter Studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
        },
        {
            // edit an app
            extra_trigger: ".o_studio_home_menu",
            trigger: `.o_app[data-menu-xmlid*="studio"]:contains(${createdAppString})`,
            run: function () {
                // We can't emulate a hover to display the edit icon
                const editIcon = this.$anchor[0].querySelector(".o_web_studio_edit_icon");
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
            trigger: ".o_web_studio_selector:eq(0)",
        },
        {
            trigger: ".o_web_studio_palette > .o_web_studio_selector:first",
        },
        {
            trigger: ".modal-footer .btn.btn-primary",
        },
        {
            // click on the created app
            trigger: `.o_app[data-menu-xmlid*="studio"]:contains(${createdAppString})`,
        },
        {
            // create a new menu
            trigger: ".o_main_navbar .o_web_edit_menu",
        },
        {
            trigger: "footer.modal-footer .js_add_menu",
        },
        {
            trigger: 'input[name="menuName"]',
            run: "text " + (createdMenuString = randomString(6)),
        },
        {
            trigger: 'div.o_web_studio_menu_creator_model_choice input[value="existing"]',
        },
        {
            trigger: "div.o_web_studio_menu_creator_model .o_record_selector input",
            run: "text a",
        },
        {
            trigger:
                ".o_record_selector .o-autocomplete--dropdown-menu > li > a:not(:has(.fa-spin))",
        },
        {
            extra_trigger: ".o_record_selector :not(.o-autocomplete dropdown-menu)",
            trigger: '.o_web_studio_add_menu_modal button:contains(Confirm):not(".disabled")',
        },
        {
            extra_trigger: ":not(.o_inactive_modal) .o-web-studio-appmenu-editor",
            trigger: '.o-web-studio-appmenu-editor button:contains(Confirm):not(".disabled")',
        },
        {
            // check that the Studio menu is still there
            extra_trigger: ".o_web_studio_menu",
            // switch to form view
            trigger: '.o_web_studio_views_icons > a[title="Form"]',
        },
        {
            // wait for the form editor to be rendered because the sidebar is the same
            extra_trigger: ".o_web_studio_form_view_editor",
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
        },
        {
            // add an new field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char",
            run: "drag_and_drop_native .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            // click on the field
            trigger: ".o_web_studio_form_view_editor .o_wrap_label:first label",
            // when it's there
            extra_trigger: '.o_web_studio_sidebar input[name="technical_name"]',
        },
        {
            // rename the label
            trigger: '.o_web_studio_sidebar input[name="string"]',
            run: "text My Coucou Field",
        },
        stepNextTick(),
        {
            // verify that the field name has changed and change it
            trigger: '.o_web_studio_sidebar input[name="technical_name"]',
            run(helper) {
                assertEqual(this.$anchor[0].value, "my_coucou_field");
                helper.text("coucou");
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
        },
        {
            // add a new field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_char",
            run: "drag_and_drop_native .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            // rename the field with the same name
            trigger: '.o_web_studio_sidebar input[name="technical_name"]',
            run: "text coucou",
        },
        {
            // an alert dialog should be opened
            trigger: ".modal-footer > button:first",
        },
        {
            // rename the label
            trigger: '.o_web_studio_sidebar input[name="string"]',
            run: "text COUCOU",
        },
        stepNextTick(),
        {
            // verify that the field name has changed (post-fixed by _1)
            trigger: '.o_web_studio_sidebar input[name="technical_name"]',
            run(helper) {
                assertEqual(this.$anchor[0].value, "coucou_1");
            },
            // the rename operation (/web_studio/rename_field + /web_studio/edit_view)
            // takes a while and sometimes reaches the default 10s timeout
            timeout: 20000,
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new",
        },
        {
            // add a monetary field --> create a currency field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_monetary",
            run: "drag_and_drop_native .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            // verify that the monetary field is in the view
            extra_trigger:
                '.o_web_studio_form_view_editor .o_wrap_label:eq(1) label:contains("New Monetary")',
            // switch the two first fields
            trigger: ".o_web_studio_form_view_editor .o_inner_group:first .o-draggable:eq(1)",
            run: "drag_and_drop_native .o_inner_group:first .o_web_studio_hook:first",
        },
        {
            // click on "Add" tab
            extra_trigger:
                '.o_web_studio_form_view_editor .o_wrap_label:eq(0) label:contains("New Monetary")',
            trigger: ".o_web_studio_sidebar .o_web_studio_new",
        },
        {
            // verify that the fields have been switched
            extra_trigger:
                '.o_web_studio_form_view_editor .o_wrap_label:eq(0) label:contains("New Monetary")',
            // add a m2m field
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_many2many",
            run: "drag_and_drop_native .o_inner_group:first .o_web_studio_hook:first",
        },
        {
            // type something in the modal
            trigger: '[name="relation_id"] input.o-autocomplete--input',
            in_modal: true,
            // we are sure "Activity" exists since studio depends on mail.
            //Also, it is determinisic and field names should not conflict too much.
            run: "text mail.activity",
        },
        {
            // select Activity as model
            trigger:
                '[name="relation_id"] .o-autocomplete--dropdown-menu li a:not(:has(.fa-spin)):contains(Activity)',
            in_modal: true,
            run(helpers) {
                const el = Array.from(this.$anchor).find((el) => el.textContent === "Activity");
                return helpers.click($(el));
            },
        },
        {
            in_modal: true,
            trigger: "button:contains(Confirm):not(.disabled)",
        },
        {
            // select the m2m to set its properties
            trigger: ".o_wrap_input:has(.o_field_many2many)",
            timeout: 15000, // creating M2M relations can take some time...
        },
        {
            // change the `widget` attribute
            trigger: '.o_web_studio_sidebar [name="widget"] .o_select_menu_toggler_slot',
        },
        {
            trigger:
                ".o_web_studio_sidebar [name='widget'] .o_select_menu_item_label:contains('(many2many_tags)')",
        },
        {
            // use colors on the m2m tags
            trigger: '.o_web_studio_sidebar [name="color_field"]',
        },
        {
            // add a statusbar
            trigger: ".o_web_studio_statusbar_hook",
        },
        {
            trigger: ".modal-footer .btn.btn-primary",
        },
        {
            trigger: ".o_statusbar_status",
        },
        {
            // verify that a default value has been set for the statusbar
            trigger:
                '.o_web_studio_sidebar [name="default_value"] .o_select_menu_toggler_slot:contains(First Status)',
            run() {},
        },
        {
            trigger: ".o_web_studio_views_icons a[title=Form]",
        },
        {
            // verify Chatter can be added after changing view to form
            extra_trigger: ".o_web_studio_add_chatter",
            // edit action
            trigger: ".o_web_studio_menu .o_menu_sections li a:contains(Views)",
        },
        {
            // edit form view
            trigger:
                '.o_web_studio_view_category .o_web_studio_view_type[data-type="form"] .o_web_studio_thumbnail',
        },
        {
            // verify Chatter can be added after changing view to form
            extra_trigger: ".o_web_studio_add_chatter",
            // switch in list view
            trigger: '.o_web_studio_menu .o_web_studio_views_icons a[title="List"]',
        },
        {
            // wait for the list editor to be rendered because the sidebar is the same
            extra_trigger: ".o_web_studio_list_view_editor",
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
        },
        {
            // add an existing field (display_name)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_field_char:contains(COUCOU)",
            run: "drag_and_drop_native .o_web_studio_list_view_editor th.o_web_studio_hook:first",
        },
        {
            // verify that the field is correctly named
            extra_trigger: '.o_web_studio_list_view_editor th:contains("COUCOU")',
            // leave Studio
            trigger: ".o_web_studio_leave > a.btn",
        },
        {
            // come back to the home menu to check if the menu data have changed
            extra_trigger: ".o_web_client:not(.o_in_studio)",
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
        },
        {
            trigger: "input.o_search_hidden",
            // Open Command Palette
            run: "text " + createdMenuString[0],
        },
        {
            trigger: ".o_command_palette_search input",
            run: "text " + "/" + createdMenuString,
        },
        {
            // search results should have been updated
            extra_trigger: `.o_command.focused:contains(${createdAppString} / ${createdMenuString})`,
            trigger: ".o_command_palette",
            // Close the Command Palette
            run: () => {
                window.dispatchEvent(
                    new KeyboardEvent("keydown", {
                        bubbles: true,
                        key: "Escape",
                    })
                );
            },
        },
        {
            trigger: ".o_home_menu",
            // go back again to the app (using keyboard)
            run: () => {
                window.dispatchEvent(
                    new KeyboardEvent("keydown", {
                        bubbles: true,
                        key: "Escape",
                    })
                );
            },
        },
        {
            // wait to be back in the list view
            extra_trigger: ".o_list_view",
            // re-open studio
            trigger: ".o_web_studio_navbar_item",
        },
        {
            // modify the list view
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
        },
        {
            //select field you want to sort and based on that sorting will be applied on List view
            trigger:
                '.o_web_studio_sidebar .o_web_studio_sidebar_select[name="sort_by"] .o_select_menu_toggler',
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_sidebar_select[name='sort_by'] .dropdown-item",
        },
        {
            //change order of sorting, Select order and change it
            trigger:
                '.o_web_studio_sidebar .o_web_studio_sidebar_select[name="sort_order"] .o_select_menu_toggler',
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_sidebar_select[name='sort_order'] .dropdown-item:nth-child(2)",
        },
        {
            // edit action
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
        },
        {
            // add a kanban
            trigger:
                '.o_web_studio_view_category .o_web_studio_view_type.o_web_studio_inactive[data-type="kanban"] .o_web_studio_thumbnail',
        },
        {
            // add a dropdown
            trigger: ".o_dropdown_kanban.o_web_studio_add_dropdown",
        },
        {
            trigger: ".modal-footer .btn.btn-primary",
        },
        {
            // select the dropdown for edition
            trigger: ".o_dropdown_kanban:not(.o_web_studio_add_dropdown)",
        },
        {
            // enable "Set Cover" feature
            trigger: ".o_web_studio_sidebar input[name=cover_value]",
        },
        {
            trigger: ".modal-footer .btn.btn-primary",
        },
        {
            // edit action
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
        },
        {
            // check that the kanban view is now active
            extra_trigger:
                '.o_web_studio_view_category .o_web_studio_view_type:not(.o_web_studio_inactive)[data-type="kanban"]',
            // add an activity view
            trigger:
                '.o_web_studio_view_category .o_web_studio_view_type.o_web_studio_inactive[data-type="activity"] .o_web_studio_thumbnail',
        },
        {
            extra_trigger: ".o_activity_view",
            // edit action
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
            timeout: 20000, // activating a view takes a while and sometimes reaches the default 10s timeout
        },
        {
            // add a graph view
            trigger:
                '.o_web_studio_view_category .o_web_studio_view_type.o_web_studio_inactive[data-type="graph"] .o_web_studio_thumbnail',
        },
        {
            extra_trigger: ".o_graph_renderer",
            trigger: '.o_web_studio_menu .o_menu_sections li a:contains("Views")',
        },
        {
            extra_trigger: ".o_web_studio_views",
            // edit the search view
            trigger:
                '.o_web_studio_view_category .o_web_studio_view_type[data-type="search"] .o_web_studio_thumbnail',
        },
        {
            extra_trigger: ".o_web_studio_search_view_editor",
            trigger: ".o_menu_toggle:not(.o_menu_toggle_back)",
        },
        {
            trigger: ".o_web_studio_home_studio_menu .dropdown-toggle",
        },
        {
            // export all modifications
            trigger: ".o_web_studio_export",
        },
        {
            // click on the created app
            trigger: '.o_app[data-menu-xmlid*="studio"]:last',
        },
        {
            // switch to form view
            trigger: '.o_web_studio_views_icons > a[title="Form"]',
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor",
            // click on the view tab
            trigger: ".o_web_studio_view",
        },
        {
            // click on the restore default view button
            trigger: ".o_web_studio_restore",
        },
        {
            // click on the ok button
            trigger: ".modal-footer .btn.btn-primary",
        },
        {
            // checks that the field doesn't exist anymore
            extra_trigger: '.o_web_studio_form_view_editor:not(:has(.o_form_label))',
            trigger: ".o_web_studio_leave > a.btn",
        },
        stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_hide_fields_tour", {
    url: "/web?debug=1#action=studio&mode=home_menu",
    test: true,
    steps: () => [
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: `
        .o_web_studio_app_creator_name
        > input`,
            run: `text ${randomString(6)}`,
        },
        {
            // make another interaction to show "next" button
            trigger: `
        .o_web_studio_selectors
        .o_web_studio_selector:eq(2)`,
        },
        {
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: `
        .o_web_studio_menu_creator
        > input`,
            run: `text ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            // check that the Studio menu is still there
            extra_trigger: ".o_web_studio_menu",
            trigger: ".o_web_studio_leave > a.btn",
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
        },
        {
            trigger: ".oe_title input",
            run: "text Test",
        },
        {
            trigger: ".o_form_button_save",
        },
        {
            trigger: ".o_web_studio_navbar_item",
        },
        {
            extra_trigger: ".o_web_studio_menu",
            trigger: `
        .o_web_studio_views_icons
        > a[title="List"]`,
        },
        {
            // wait for the list editor to be rendered because the sidebar is the same
            extra_trigger: ".o_web_studio_list_view_editor",
            trigger: ".o_web_studio_existing_fields_header",
        },
        {
            trigger: `
        .o_web_studio_sidebar
        .o_web_studio_existing_fields
        .o_web_studio_component:has(.o_web_studio_component_description:contains(display_name))`,
            run: "drag_and_drop_native .o_web_studio_list_view_editor .o_web_studio_hook",
        },
        {
            trigger: `
        .o_list_table
        th[data-name="display_name"]`,
        },
        {
            trigger: `
        .o_web_studio_sidebar
        [name="optional"] .o_select_menu_toggler`,
        },
        {
            trigger:
                ".o_web_studio_sidebar [name='optional'] .o_select_menu_item:contains(Hide by default)",
        },
        {
            extra_trigger: '.o_list_table:not(:has(th[data-name="display_name"]))',
            trigger: `
        .o_web_studio_sidebar
        .o_web_studio_view`,
        },
        {
            trigger: `
        .o_web_studio_sidebar_checkbox
        input#show_invisible`,
        },
        {
            extra_trigger: `
        .o_list_table
        th[data-name="display_name"].o_web_studio_show_invisible`,
            trigger: ".o_web_studio_leave > a.btn",
        },
        stepNotInStudio(".o_list_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_model_option_value_tour", {
    url: "/web?debug=tests#action=studio&mode=home_menu",
    test: true,
    steps: () => [
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: `
        .o_web_studio_app_creator_name
        > input`,
            run: `text ${randomString(6)}`,
        },
        {
            trigger: `
        .o_web_studio_selectors
        .o_web_studio_selector:eq(2)`,
        },
        {
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: `
        .o_web_studio_menu_creator
        > input`,
            run: `text ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            // check monetary value in model configurator
            trigger: 'input[name="use_value"]',
        },
        {
            // check lines value in model configurator
            trigger: 'input[name="lines"]',
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            trigger: '.o_web_studio_menu .o_web_studio_views_icons > a[title="Graph"]',
            timeout: 60000 /* previous step reloads registry, etc. - could take a long time */,
        },
        {
            // wait for the graph editor to be rendered and also check for sample data
            extra_trigger: ".o_view_sample_data .o_graph_renderer",
            trigger: '.o_web_studio_menu .o_web_studio_views_icons a[title="Pivot"]',
        },
        {
            // wait for the pivot editor to be rendered and also check for sample data
            extra_trigger: ".o_pivot_view .o_view_sample_data .o_view_nocontent_empty_folder",
            trigger: ".o_web_studio_leave > a.btn",
        },
        stepNotInStudio(".o_pivot_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_new_report_tour", {
    url: "/web",
    test: true,
    steps: () => [
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            // click on the created app
            trigger: '.o_app[data-menu-xmlid*="studio"]:first',
            extra_trigger: "body.o_in_studio",
        },
        {
            // edit reports
            trigger: ".o_web_studio_menu li a:contains(Reports)",
        },
        {
            // create a new report
            trigger: ".o_control_panel .o-kanban-button-new",
        },
        {
            // select external layout
            trigger: '.o_web_studio_report_layout_dialog div[data-layout="web.external_layout"]',
        },
        {
            // edit report name
            trigger: '.o_web_studio_sidebar input[id="name"]',
            run: "text My Awesome Report",
        },
        {
            // add a new group on the node
            trigger: '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] input',
            run: function () {
                this.$anchor.click();
            },
        },
        {
            trigger: ".o-autocomplete--dropdown-menu li:contains(Access Rights)",
        },
        {
            // wait for the group to appear
            trigger:
                '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] .o_tag_badge_text:contains(Access Rights)',
            run() {},
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg iframe .odoo-editor-editable div.page div",
            run($anchor) {
                const element = this.$anchor[0];
                element.ownerDocument.getSelection().setPosition(element);
                assertEqual(element.outerHTML, `<div class="oe_structure"></div>`);
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg iframe .odoo-editor-editable div.page div",
            run() {
                const element = this.$anchor[0];
                assertEqual(element.classList.contains("oe-command-temporary-hint"), true);
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg iframe .odoo-editor-editable div.page div",
            run: "text some new text",
        },
        {
            trigger: ".o_web_studio_menu .o-web-studio-save-report.btn-primary",
        },
        {
            // The report has been saved
            trigger: ".o_web_studio_menu .o-web-studio-save-report:not(.btn-primary)",
            run() {},
        },
        {
            trigger: ".o_web_studio_breadcrumb .o_back_button:contains(Reports)",
        },
        {
            // a invisible element cannot be used as a trigger so this small hack is
            // mandatory for the next step
            run: function () {
                $(".o_kanban_record:contains(My Awesome Report) .dropdown-toggle").css(
                    "visibility",
                    "visible"
                );
            },
            trigger: ".o_kanban_view",
        },
        {
            // open the dropdown
            trigger: ".o_kanban_record:contains(My Awesome Report) .dropdown-toggle",
        },
        {
            // duplicate the report
            trigger:
                ".o_kanban_record:contains(My Awesome Report) .dropdown-menu a:contains(Duplicate)",
        },
        {
            // open the duplicate report
            trigger: ".o_kanban_record:contains(My Awesome Report copy(1))",
        },
        {
            // switch to 'Report' tab
            trigger: ".o_web_studio_sidebar input[id='name']",
            run() {
                assertEqual(this.$anchor[0].value, "My Awesome Report copy(1)");
            },
        },
        {
            trigger: ".o-web-studio-report-editor-wysiwyg iframe div.page div",
            run() {
                assertEqual(this.$anchor[0].textContent, "some new text");
            },
        },
        {
            trigger:
                '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] .o_tag_badge_text:contains(Access Rights)',
            run() {},
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
        },
        stepNotInStudio(),
    ],
});

registry.category("web_tour.tours").add("web_studio_new_report_basic_layout_tour", {
    url: "/web",
    test: true,
    steps: () => [
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            // click on the created app
            trigger: '.o_app[data-menu-xmlid*="studio"]:first',
            extra_trigger: "body.o_in_studio",
        },
        {
            // edit reports
            trigger: ".o_web_studio_menu li a:contains(Reports)",
        },
        {
            // create a new report
            trigger: ".o_control_panel .o-kanban-button-new",
        },
        {
            // select basic layout
            trigger: '.o_web_studio_report_layout_dialog div[data-layout="web.basic_layout"]',
        },
        {
            // edit report name
            trigger: '.o_web_studio_sidebar input[id="name"]',
            run: "text My Awesome basic layout Report",
        },
        {
            // add a new group on the node
            trigger: '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] input',
            run: function () {
                this.$anchor.click();
            },
        },
        {
            trigger: ".o-autocomplete--dropdown-menu li:contains(Access Rights)",
        },
        {
            // wait for the group to appear
            trigger:
                '.o_web_studio_sidebar .o_field_many2many_tags[name="groups_id"] .o_tag_badge_text:contains(Access Rights)',
            run() {},
        },
        {
            trigger: ".o_web_studio_menu .o-web-studio-save-report.btn-primary",
        },
        {
            // The report has been saved
            trigger: ".o_web_studio_menu .o-web-studio-save-report:not(.btn-primary)",
            run() {},
        },
        {
            // leave the report
            trigger: ".o_web_studio_breadcrumb .o_back_button:contains(Reports)",
        },
        {
            // a invisible element cannot be used as a trigger so this small hack is
            // mandatory for the next step
            run: function () {
                $(".o_kanban_record:contains(My Awesome basic layout Report) .dropdown-toggle").css(
                    "visibility",
                    "visible"
                );
            },
            trigger: ".o_kanban_view",
        },
        {
            // open the dropdown
            trigger: ".o_kanban_record:contains(My Awesome basic layout Report) .dropdown-toggle",
        },
        {
            // duplicate the report
            trigger:
                ".o_kanban_record:contains(My Awesome basic layout Report) .dropdown-menu a:contains(Duplicate)",
        },
        {
            // open the duplicate report
            trigger: ".o_kanban_record:contains(My Awesome basic layout Report copy(1))",
        },
        {
            trigger: '.o_web_studio_sidebar input[id="name"]',
            run() {
                assertEqual(this.$anchor[0].value, "My Awesome basic layout Report copy(1)");
            },
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
        },
        stepNotInStudio(),
    ],
});

registry.category("web_tour.tours").add("web_studio_approval_tour", {
    url: "/web?debug=1",
    test: true,
    steps: () => [
        {
            // go to Apps menu
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
        },
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_cp_switch_buttons",
        },
        {
            // switch to form view editor
            trigger: '.o_web_studio_views_icons > a[title="Form"]',
        },
        {
            // click on first button it finds that has a node id
            trigger: ".o_web_studio_form_view_editor button.o-web-studio-editor--element-clickable",
        },
        {
            // enable approvals for the button
            trigger: '.o_web_studio_sidebar label[for="studio_approval"]',
        },
        {
            // add approval rule
            trigger: '.o_web_studio_sidebar_approval [name="create_approval_rule"]',
            extra_trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            // set approval message
            trigger: '.o_web_studio_sidebar_approval input[name*="approval_message"]',
            run: "text nope",
        },
        {
            // set domain on first rule
            trigger: ".o_web_studio_sidebar_approval .o_approval_domain",
            extra_trigger: ".o_studio_sidebar_approval_rule:eq(1)",
        },
        {
            // set stupid domain that is always truthy
            trigger: ".o_domain_selector_debug_container textarea",
            run: function () {
                this.$anchor.focusIn();
                this.$anchor.val('[["id", "!=", False]]');
                this.$anchor.change();
            },
        },
        {
            // save domain and close modal
            trigger: " .modal-footer .btn-primary",
        },
        {
            // add second approval rule when the first is set
            trigger: '.o_web_studio_sidebar_approval [name="create_approval_rule"]',
            extra_trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            // enable 'force different users' for one rule (doesn't matter which)
            trigger: '.o_web_studio_sidebar label[for*="exclusive_user"]',
            extra_trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            // leave studio
            trigger: ".o_web_studio_leave > a.btn",
            extra_trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            // go back to kanban
            trigger: ".o_breadcrumb .o_back_button",
            extra_trigger: ".o_web_client:not(.o_in_studio)",
        },
        {
            // open first record (should be the one that was used, so the button should be there)
            trigger: ".o_kanban_view .o_kanban_record .o_dropdown_kanban .dropdown-toggle",
        },
        {
            trigger: ".o_kanban_view .o_kanban_record .o-dropdown--menu .dropdown-item",
        },
        {
            // try to do the action
            trigger: "button[studio_approval]",
        },
        {
            // there should be a warning
            trigger: ".o_notification.border-warning",
        },
        {
            trigger: ".breadcrumb .o_back_button",
        },
        {
            trigger: "body .o_modules_kanban",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_custom_field_tour", {
    url: "/web",
    test: true,
    steps: () => [
        {
            // go to Apps menu
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
        },
        {
            // click on the list view
            trigger: ".o_switch_view.o_list",
        },
        {
            // click on optional column dropdown
            trigger: ".o_optional_columns_dropdown_toggle",
        },
        {
            // click on add custom field
            trigger: ".dropdown-item-studio",
        },
        {
            // go to home menu
            trigger: ".o_menu_toggle",
            extra_trigger: ".o_web_client.o_in_studio",
        },
        {
            //leave studio
            trigger: ".o_web_studio_leave > a.btn",
        },
        {
            // studio left.
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            extra_trigger: ".o_web_client:not(.o_in_studio)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_local_storage_tour", {
    url: "/web",
    test: true,
    steps: () => [
        {
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            run: function () {
                localStorage.setItem("openStudioOnReload", "main");
                window.location.reload();
            },
        },
        {
            // should be directly in studio mode
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            extra_trigger: ".o_web_client.o_in_studio",
        },
        {
            trigger: ".o_menu_toggle",
        },
        {
            trigger: ".o_web_studio_leave > a.btn",
        },
        {
            // studio left.
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            extra_trigger: ".o_web_client:not(.o_in_studio)",
            run: function () {
                window.location.reload();
            },
        },
        {
            // studio left after refresh.
            trigger: '.o_app[data-menu-xmlid="base.menu_management"]',
            extra_trigger: ".o_web_client:not(.o_in_studio)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_custom_background_tour", {
    url: "/web",
    test: true,
    steps: () => [
        {
            content: "class for custom background must be enabled (outside studio)",
            trigger: ".o_home_menu_background_custom.o_home_menu_background:not(.o_in_studio)",
            run: () => null,
        },
        {
            content: "opening studio",
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
        },
        {
            content: "class for custom background must be enabled (in studio)",
            trigger: ".o_home_menu_background_custom.o_home_menu_background.o_in_studio",
            run: () => null,
        },
        {
            content: "click on Customizations button",
            trigger: ".o_web_studio_home_studio_menu button",
        },
        {
            content: "reset the background",
            trigger: ".o_web_studio_reset_default_background",
        },
        {
            content: "validate the reset of the background",
            trigger: ".modal-dialog .btn-primary",
        },
        {
            content: "class for custom background must be disabled (inside studio)",
            trigger: ".o_home_menu_background.o_in_studio:not(.o_home_menu_background_custom)",
            run: () => null,
        },
        {
            content: "leaving studio",
            trigger: ".o_web_studio_leave a",
        },
        {
            content: "class for custom background must be disabled (outside studio)",
            trigger: ".o_home_menu_background:not(.o_in_studio.o_home_menu_background_custom)",
            run: () => null,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_create_app_with_pipeline_and_user_assignment", {
    test: true,
    steps: () => [
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            // the next steps are here to create a new app
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: "text " + (createdAppString = randomString(6)),
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: "text " + (createdMenuString = randomString(6)),
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            trigger: "input#use_stages",
        },
        {
            trigger: "input#use_responsible",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            trigger: ".o_web_studio_editor .o_menu_sections a:contains(Views)",
        },
        {
            trigger: ".o_web_studio_view_type[data-type='kanban'] .o_web_studio_thumbnail",
        },
        {
            extra_trigger: ".o_web_studio_kanban_view_editor",
            trigger: "img.oe_kanban_avatar",
            run() {
                const avatarImg = document.querySelector("img.oe_kanban_avatar");
                if (!avatarImg.getAttribute("title") === "Unassigned") {
                    throw new Error(
                        "The title of the new avatar should be set, even if there are no record"
                    );
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_alter_field_existing_in_multiple_views_tour", {
    test: true,
    steps: () => [
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item button",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            // the next steps are here to create a new app
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: "text " + (createdAppString = randomString(6)),
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: `text ${createdAppString}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            extra_trigger: ".o_web_studio_sidebar",
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
            timeout: 60000,
        },
        {
            // add an existing field (the one we created)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(2) .o_web_studio_field_many2many:contains(Followers (Partners))",
            run: "drag_and_drop_native .o_inner_group:first .o_web_studio_hook:first",
        },
        {
            trigger: ".o_web_studio_new ",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_many2many",
            run: "drag_and_drop_native div.o_web_studio_hook:last",
        },
        {
            extra_trigger: ".modal-body",
            in_modal: true,
            trigger: '[name="relation_id"] input',
            run: `text ${createdAppString}`,
        },
        {
            // select the first model
            trigger: ".o-autocomplete--dropdown-menu > li > a:not(:has(.fa-spin))",
            in_modal: true,
        },
        {
            trigger: "button:contains(Confirm)",
        },
        {
            // edit list view
            trigger: ".o_web_studio_editX2Many",
        },
        {
            // wait for list view to be loaded
            extra_trigger: ".o_web_studio_list_view_editor",
            // go to view
            trigger: ".o_web_studio_view ",
        },
        {
            // show invisible elements
            trigger: 'label[for="show_invisible"]',
        },
        {
            trigger: ".o_web_studio_new ",
        },
        {
            // unfold 'Existing Fieldqs' section
            trigger: ".o_web_studio_existing_fields_header",
        },
        {
            // add an existing field (the one we created)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_field_type_container:eq(1) .o_web_studio_field_many2many:contains(Followers (Partners))",
            run: "drag_and_drop_native .o_web_studio_list_view_editor th.o_web_studio_hook:first",
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
            extra_trigger: ".o_web_studio_snackbar .fa.fa-check",
            // check if the invisible option is checked
            trigger: "#invisible:checked",
            run() {},
        },
    ],
});

const buttonToogleStudio = {
    trigger: `button[title="Toggle Studio"]`,
};
const addActionButtonModalSteps = (
    ActionLabel = "web_studio_new_button_action_name",
    ActionName = "Privacy Lookup"
) => [
    {
        trigger: ".o-web-studio-editor--add-button-action",
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action input#set_label",
        run: `text ${ActionLabel}`,
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action input#set_button_type_to_action",
    },
    {
        trigger: ".o-web-studio-editor--modal-add-action .o_record_selector input",
        run: `text ${ActionName}`,
    },
    {
        trigger: `.o-web-studio-editor--modal-add-action .o-autocomplete--dropdown-menu li a:not(:has(.fa-spin)):contains(${ActionName})`,
        run(helpers) {
            const el = Array.from(this.$anchor).find((el) => el.textContent === ActionName);
            return helpers.click($(el));
        },
    },
    {
        trigger: "footer button.o-web-studio-editor--add-button-confirm",
    },
];

const addMethodButtonModalSteps = (
    ) => [
        {
            trigger: ".o-web-studio-editor--add-button-action",
        },
        {
            trigger: ".o-web-studio-editor--modal-add-action input#set_label",
            run: `text test`,
        },
        {
            trigger: ".o-web-studio-editor--modal-add-action input#set_button_type_to_object",
        },
        {
            trigger: ".o-web-studio-editor--modal-add-action  input#set_method",
            run: `text demo`,
        },

    ];

registry.category("web_tour.tours").add("web_studio_check_method_in_model", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
            {
            trigger: ".o_form_view .o_form_editable",
        },
        buttonToogleStudio,
        ...addMethodButtonModalSteps(),
        {
            trigger: "div.text-danger",
            run() {
                const div_error = document.querySelector("div.text-danger");
                assertEqual(div_error.innerHTML, "The method demo does not exist on the model res.partner().")
                },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_action_button_in_form_view", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        buttonToogleStudio,
        ...addActionButtonModalSteps(),
        {
            trigger: ".o_web_studio_leave a",
        },
        stepNotInStudio(".o_form_view"),
    ],
});

registry
    .category("web_tour.tours")
    .add("web_studio_test_create_second_action_button_in_form_view", {
        test: true,
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            },
            {
                trigger: ".o_form_view .o_form_editable",
            },
            buttonToogleStudio,
            ...addActionButtonModalSteps("web_studio_other_button_action_name", "Download (vCard)"),
            {
                trigger: ".o_web_studio_leave a",
            },
            stepNotInStudio(".o_form_view"),
        ],
    });

registry.category("web_tour.tours").add("web_studio_test_create_action_button_in_list_view", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        buttonToogleStudio,
        {
            trigger: ".o_web_studio_views_icons a[aria-label='List']",
        },
        {
            trigger: ".o_optional_columns_dropdown button",
        },
        ...addActionButtonModalSteps(),
        {
            trigger: ".o_web_studio_leave a",
        },
        stepNotInStudio(".o_list_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_remove_action_button_in_form_view", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        buttonToogleStudio,
        {
            trigger: 'button[studioxpath="/form[1]/header[1]/button[1]"]',
        },
        {
            trigger: "button.o_web_studio_remove",
        },
        {
            trigger: "footer.modal-footer>button.btn-primary",
        },
        {
            trigger: ".o_web_studio_leave a",
        },
        stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_remove_action_button_in_list_view", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        buttonToogleStudio,
        {
            trigger: ".o_web_studio_views_icons a[aria-label='List']",
        },
        {
            trigger: ".o_optional_columns_dropdown button",
        },
        {
            trigger: 'button[studioxpath="/tree[1]/header[1]/button[1]"]',
        },
        {
            trigger: "button.o_web_studio_remove",
        },
        {
            trigger: "footer.modal-footer>button.btn-primary",
        },
        {
            trigger: ".o_web_studio_leave a",
        },
        stepNotInStudio(".o_list_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_create", {
    url: "/web?debug=1",
    test: true,
    steps: () => [
        // This tour drag&drop a monetary field and verify that a currency is created
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: () => {},
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
        },
        // drag&drop a monetary and verify that the currency is in the view
        {
            // add a new monetary field
            trigger: ".o_web_studio_sidebar .o_web_studio_field_monetary",
            run: "drag_and_drop_native .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            // verify that the currency is set
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field .text-start",
            run() {
                assertEqual(this.$anchor[0].textContent, "Currency (x_studio_currency_id)");
            },
        },
        {
            // currency field is in the view
            trigger: ".o_web_studio_view_renderer div[data-field-name='x_studio_currency_id']",
        },
        {
            trigger: ".o_web_studio_properties.active",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_change_currency_name", {
    url: "/web?debug=1",
    test: true,
    steps: () => [
        // Changing currency name also change the currency name in the monetary currency selection
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: () => {},
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
        },
        {
            // currency field is in the view and click on it
            trigger: ".o_web_studio_view_renderer [data-field-name='x_studio_currency_test']",
        },
        {
            // change the currency name
            trigger: "input[name='string']",
            run(helper) {
                helper.text("NewCurrency");
            },
        },
        {
            // click on monetary
            trigger: "div[data-field-name^='x_studio_monetary_test']",
        },
        {
            // verify that the currency name changed in the monetary field
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field .text-start",
            run() {
                assertEqual(this.$anchor[0].textContent, "NewCurrency (x_studio_currency_test)");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_related_monetary_creation", {
    url: "/web?debug=1",
    test: true,
    steps: () => [
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: () => {},
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
        },
        {
            // add a new related field
            trigger: ".o_web_studio_sidebar .o_web_studio_field_related",
            run: "drag_and_drop_native .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            trigger: '.o_model_field_selector_value',
        },
        {
            in_modal: false,
            trigger:
                ".o_model_field_selector_popover_search input",
            run: "text X Test",
        },
        {
            in_modal: false,
            trigger: ".o_model_field_selector_popover_item[data-name='x_test'] .o_model_field_selector_popover_item_relation",
        },
        {
            in_modal: false,
            trigger:
                ".o_model_field_selector_popover_search input",
            run: "text X Studio Monetary Test",
        },
        {
            in_modal: false,
            trigger: ".o_model_field_selector_popover_item[data-name='x_studio_monetary_test'] button",
        },
        {
            trigger:".modal-footer button.btn-primary",
        },
        {
            // The related monetary is created
            trigger: ".o_web_studio_view_renderer .o_form_label:contains('New Related Field')",
        },
        {
            // The currency is created
            trigger: ".o_web_studio_view_renderer [data-field-name='x_studio_currency_id']",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_change_currency_field", {
    url: "/web",
    test: true,
    steps: () => [
        // Change currency and verify that the view take the changes into account (the dollar appears)
        {
            // open the custom app form view
            trigger: "a[data-menu-xmlid='web_studio.studio_app_menu']",
        },
        {
            // fill the required char input
            trigger: ".o_field_char input",
            run: "text title",
        },
        {
            // fill the new currency (many2one) input #1
            trigger: "div [name='x_studio_currency_test2'] input",
            run: "text USD",
        },
        {
            // add a new currency field step #2
            trigger: '.ui-menu-item a:contains("USD")',
        },
        {
            // save the view form
            trigger: "button.o_form_button_save",
        },
        {
            // open studio with the record
            trigger: ".o_main_navbar .o_web_studio_navbar_item button",
            extra_trigger: ".o_form_saved",
        },
        {
            // check that there is no currency symbol in renderer
            trigger: "div[name='x_studio_monetary_test'] span",
            run() {
                assertEqual(this.$anchor[0].textContent, "0.00");
            },
        },
        {
            // click on the monetary field
            trigger: "div[data-field-name='x_studio_monetary_test']",
        },
        {
            // change the currency_field in the monetary
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field button",
        },
        {
            // click on the second currency, which is "X Studio Currency Test2"
            trigger: ".o_web_studio_property_currency_field .o_select_menu_item:nth-child(2)",
        },
        {
            //wait until the currency has been set (also test the reactivity)
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property_currency_field span.text-start:contains('X Studio Currency Test2')",
            run() {},
        },
        {
            // by changing the currency, we should have a $ symbol in the renderer
            trigger: "div[name^='x_studio_monetary'] span",
            run() {
                assertEqual(this.$anchor[0].textContent, "$ 0.00");
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_change_currency_not_in_view", {
    url: "/web",
    test: true,
    steps: () => [
        // Change a currency that is not present in the view insert it in the view
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: () => {},
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
        },
        {
            // click on the monetary field
            trigger: "div[data-field-name='x_studio_monetary_test']",
        },
        {
            // change the currency_field in the monetary
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field button",
        },
        {
            // click on the second currency, which is "X Studio Currency Test2"
            trigger: ".o_web_studio_property_currency_field .o_select_menu_item:nth-child(2)",
        },
        {
            // wait until the currency has been set
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property_currency_field span.text-start:contains('X Studio Currency Test2')",
            run() {},
        },
        {
            // go to view tab
            trigger: ".o_web_studio_view",
        },
        {
            // currency field is in the view and click on it
            trigger: ".o_web_studio_view_renderer div[data-field-name='x_studio_currency_test2']",
        },
        {
            trigger: ".o_web_studio_properties.active",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_monetary_add_existing_monetary", {
    url: "/web?debug=1",
    test: true,
    steps: () => [
        // Add an existing monetary trough the "existing fields" and verify that the currency
        // is added to the view
        {
            // open studio
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
            run: () => {},
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
        },
        {
            // click on "existing fields"
            trigger: ".o_web_studio_existing_fields_header",
        },
        {
            // add the existing monetary field
            trigger: ".o_web_studio_existing_fields_section .o_web_studio_field_monetary",
            run: "drag_and_drop_native .o_form_renderer .o_web_studio_hook",
        },
        {
            // monetary exist and click on monetary
            trigger: "div[data-field-name='x_studio_monetary_test']",
        },
        {
            // verify that the currency name changed in the monetary field
            trigger: ".o_web_studio_sidebar .o_web_studio_property_currency_field .text-start",
            run() {
                assertEqual(
                    this.$anchor[0].textContent,
                    "X Studio Currency Test (x_studio_currency_test)"
                );
            },
        },
        {
            // currency field is in the view
            trigger: "div[data-field-name='x_studio_currency_test']",
            run() {},
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("web_studio_monetary_create_monetary_with_existing_currency", {
        url: "/web?debug=1",
        test: true,
        steps: () => [
            // Add a new monetary field, since a currency already exists, it should take it instead
            // of creating a new one
            {
                // open studio
                trigger: ".o_main_navbar .o_web_studio_navbar_item",
                extra_trigger: ".o_home_menu_background",
            },
            {
                trigger: ".o_web_studio_new_app",
                run: () => {},
            },
            {
                trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
            },
            {
                // go to Add tab
                trigger: ".o_web_studio_new",
            },
            {
                // add a new monetary field
                trigger: ".o_web_studio_sidebar .o_web_studio_field_monetary",
                run: "drag_and_drop_native .o_web_studio_form_view_editor .o_inner_group",
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
    url: "/web?debug=1",
    test: true,
    steps: () => [
        {
            trigger: ".o_main_navbar .o_web_studio_navbar_item",
            extra_trigger: ".o_home_menu_background",
        },
        {
            trigger: ".o_web_studio_new_app",
        },
        {
            trigger: ".o_web_studio_app_creator_next",
        },
        {
            trigger: ".o_web_studio_app_creator_name > input",
            run: `text ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            trigger: ".o_web_studio_menu_creator > input",
            run: `text ${randomString(6)}`,
        },
        {
            trigger: ".o_web_studio_app_creator_next.is_ready",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            trigger: ".o_web_studio_views_icons a:last",
        },
        {
            trigger: `
        .o_web_studio_sidebar
        .o_web_studio_existing_fields
        .o_web_studio_component:has(.o_web_studio_component_description:contains(create_date))`,
            run: "drag_and_drop_native .o-web-studio-search--groupbys .o_web_studio_hook",
        },
    ],
});
