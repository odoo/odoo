/** @odoo-module */
import { registry } from "@web/core/registry";
import { stepNotInStudio, assertEqual } from "@web_studio/../tests/tours/tour_helpers";
import { queryFirst, drag, waitFor } from "@odoo/hoot-dom";
import { rpcBus } from "@web/core/network/rpc";

registry
    .category("web_tour.tours")
    .add("web_studio_test_form_view_not_altered_by_studio_xml_edition", {
        url: "/odoo?debug=1",
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
                run: "click",
            },
            {
                trigger: ".o_form_view .o_form_editable",
                run: "click",
            },
            {
                trigger: ".o_web_studio_navbar_item button:enabled",
                run: "click",
            },
            {
                trigger: ".o_web_studio_sidebar .o_web_studio_view",
                run: "click",
            },
            {
                trigger: ".o_web_studio_open_xml_editor",
                run: "click",
            },
            {
                trigger: ".o_web_studio_code_editor_info",
            },
            {
                trigger: ".o_web_studio_leave",
                run: "click",
            },
            ...stepNotInStudio(".o_form_view .o_form_editable"),
        ],
    });

/* global ace */
registry.category("web_tour.tours").add("web_studio_test_edit_with_xml_editor", {
    url: "/odoo?debug=1",
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".someDiv:not(:visible)",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_open_xml_editor",
            run: "click",
        },
        {
            trigger: ".o_web_studio_xml_editor",
        },
        {
            trigger: ".o_web_studio_xml_resource_selector .o_select_menu_toggler",
            run: "click",
        },
        {
            trigger: ".o-dropdown--menu .o_select_menu_item:contains(Odoo Studio)",
            run: "click",
        },
        {
            trigger: ".ace_content",
            run() {
                ace.edit(document.querySelector(".ace_editor")).setValue("<data/>");
            },
        },
        {
            trigger: ".o_web_studio_xml_editor .o_web_studio_xml_resource_selector .btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_snackbar:not(:has(.fa-spin))",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            run() {
                if (document.querySelector(".someDiv")) {
                    throw new Error("The edition of the view's arch via the xml editor failed");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_enter_x2many_edition_and_add_field", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='user_ids']",
            run: "click",
        },
        {
            trigger: ".o-web-studio-edit-x2manys-buttons",
        },
        {
            trigger: ".o_web_studio_editX2Many[data-type='form']",
            run: "click",
        },
        {
            trigger: ".o_view_controller.o_form_view.test-user-form",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run() {
                queryFirst(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)"
                ).scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='log_ids']",
            run() {
                const countFields = document.querySelectorAll(
                    ".o_web_studio_form_view_editor .o_field_widget"
                ).length;
                if (!countFields === 2) {
                    throw new Error("There should be 2 fields in the form view");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_enter_x2many_auto_inlined_subview", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor .o_field_widget[name='user_ids'] .o_field_x2many_list",
            run: "click",
        },
        {
            trigger: ".o-web-studio-edit-x2manys-buttons",
        },
        {
            trigger: ".o_web_studio_editX2Many[data-type='list']",
            run: "click",
        },
        {
            trigger: ".o_view_controller.o_list_view.test-user-list",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run() {
                queryFirst(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)"
                ).scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run: "drag_and_drop(.o_web_studio_list_view_editor .o_web_studio_hook:eq(1))",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='log_ids']",
            run() {
                const countFields = document.querySelectorAll(
                    ".o_web_studio_form_view_editor th[data-name]"
                ).length;
                if (!countFields === 2) {
                    throw new Error("There should be 2 fields in the form view");
                }
            },
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("web_studio_enter_x2many_auto_inlined_subview_with_multiple_field_matching", {
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
                run: "click",
            },
            {
                trigger: ".o_form_view .o_form_editable",
                run: "click",
            },
            {
                trigger: ".o_web_studio_navbar_item button:enabled",
                run: "click",
            },
            {
                trigger:
                    ".o_web_studio_form_view_editor .o_field_widget[name='user_ids']:eq(1) .o_field_x2many_list",
                run: "click",
            },
            {
                trigger: ".o-web-studio-edit-x2manys-buttons",
            },
            {
                trigger: ".o_web_studio_editX2Many[data-type='list']",
                run: "click",
            },
            {
                trigger: ".o_view_controller.o_list_view.test-user-list",
            },
            {
                trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
                run: "click",
            },
            {
                trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
            },
            {
                trigger:
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
                run() {
                    queryFirst(
                        ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)"
                    ).scrollIntoView();
                },
            },
            {
                trigger:
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
                run: "drag_and_drop(.o_web_studio_list_view_editor .o_web_studio_hook:eq(1))",
            },
            {
                trigger: ".o_web_studio_list_view_editor th[data-name='log_ids']",
                run() {
                    const countFields = document.querySelectorAll(
                        ".o_web_studio_form_view_editor th[data-name]"
                    ).length;
                    if (!countFields === 2) {
                        throw new Error("There should be 2 fields in the form view");
                    }
                },
            },
        ],
    });

registry.category("web_tour.tours").add("web_studio_boolean_field_drag_and_drop", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_boolean",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_web_studio_hook:eq(0))",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_wrap_field_boolean .o_wrap_label",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_web_studio_hook:eq(2))",
        },
        {
            trigger: ".o_wrap_label:eq(1):contains('New CheckBox')",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_field_with_group", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_list_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='function']",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run() {
                queryFirst(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)"
                ).scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run: "drag_and_drop(.o_web_studio_list_view_editor th.o_web_studio_hook:eq(2))",
        },
        {
            trigger:
                ".o_web_studio_list_view_editor th.o_web_studio_hook:not(.o_web_studio_nearest_hook)",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='website']",
            run() {
                const countFields = document.querySelectorAll(
                    ".o_web_studio_list_view_editor th[data-name]"
                ).length;
                if (!countFields === 3) {
                    throw new Error("There should be 3 fields in the form view");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_set_tree_node_conditional_invisibility", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_list_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='title']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_attrs[data-type=invisible]",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_value",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover_item_name:contains('Display Name')",
            run: "click",
        },
        {
            trigger: ".o_tree_editor_condition input.o_input",
            run: "edit Robert && click body",
        },
        {
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='title']",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_elements_with_groups_form", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run() {
                queryFirst(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)"
                ).scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_inner_group .o_web_studio_hook:eq(1))",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor .o_web_studio_hook:not(.o_web_studio_nearest_hook)",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='website']:not(:visible)",
            run() {
                const countFields = document.querySelectorAll(
                    ".o_web_studio_form_view_editor .o_field_widget[name]"
                ).length;
                if (!countFields === 2) {
                    throw new Error("There should be 2 fields in the form view");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_element_group_in_sidebar", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='display_name']",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='display_name']",
            run: "click",
        },
        {
            trigger: ".o_field_many2many_tags[name='groups_id'] .badge",
            run() {
                const tag = document.querySelector(
                    ".o_field_many2many_tags[name='groups_id'] .badge"
                );
                if (!tag || !tag.textContent.includes("Test Group")) {
                    throw new Error("The groups should be displayed in the sidebar");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_custom_selection_field_edit_values", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_selection",
            run: "drag_and_drop(.o_web_studio_hook:eq(0))",
        },
        {
            trigger: ".o_web_studio_add_selection .o-web-studio-interactive-list-item-input",
            run: "edit some value",
        },
        {
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ".o_web_studio_leave",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_wrap_input:has(.o_field_selection)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_edit_selection_values",
            run: "click",
        },
        {
            trigger:
                ".modal:not(.o_inactive_modal) .o_web_studio_add_selection .o-web-studio-interactive-list-item-input",
            run: "edit another value cancel",
        },
        {
            trigger: ".o_web_studio_add_selection .o-web-studio-interactive-list-edit-item",
            run: "click",
        },
        {
            trigger: ".o_web_studio_selection_editor li:nth-child(2)",
            async run() {
                assertEqual(this.anchor.textContent, "another value cancel");
            },
        },
        {
            trigger: ".modal-footer .btn-secondary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_edit_selection_values",
            run: "click",
        },
        {
            trigger: ".o_web_studio_selection_editor li",
            run() {
                assertEqual(this.anchor.textContent, "some value");
            },
        },
        {
            trigger:
                ".modal:not(.o_inactive_modal) .o_web_studio_add_selection .o-web-studio-interactive-list-item-input",
            run: "edit another value",
        },
        {
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ".o_web_studio_leave",
            run: "click",
        },
        ...stepNotInStudio(),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_one2many_lines_then_edit_name", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_lines",
            run: "drag_and_drop(.o_web_studio_hook:eq(0))",
        },
        {
            trigger: ".o_field_x2many_list",
        },
        {
            trigger: ".o_form_label",
            timeout: 20000,
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_properties.active",
        },
        {
            trigger: "input[name='string']",
            run: "edit new name && click body",
        },
        {
            trigger: ".o_web_studio_leave",
            timeout: 20000,
            run: "click",
        },
        ...stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_address_view_id_no_edit", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_address_format",
            run: function () {
                if (
                    this.anchor.querySelectorAll("[name=lang]").length ||
                    !this.anchor.querySelectorAll("[name=street]").length
                ) {
                    throw new Error(
                        "The address view id set on the company country should be displayed"
                    );
                }
            },
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer",
        },
        {
            trigger: ".o_address_format",
            run: function () {
                if (
                    this.anchor.querySelectorAll("[name=street]").length ||
                    !this.anchor.querySelectorAll("[name=lang]").length
                ) {
                    throw new Error(
                        "The address view id set on the company country shouldn't be editable"
                    );
                }
            },
        },
        {
            trigger: ".o_field_widget[name='lang']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[id='required']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_snackbar .fa-check",
        },
        {
            trigger: ".o_address_format",
            run: function () {
                if (
                    this.anchor.querySelectorAll("[name=street]").length ||
                    !this.anchor.querySelectorAll("[name=lang]").length
                ) {
                    throw new Error(
                        "The address view id set on the company country shouldn't be editable"
                    );
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_new_model_from_existing_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_kanban_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_create_new_model",
            run: "click",
        },
        {
            trigger: ".modal-dialog",
        },
        {
            trigger: "input[name='model_name']",
            run: "edit new model",
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
            trigger: ".o_form_view",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_model_with_clickable_stages", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_create_new_model",
            run: "click",
        },
        {
            trigger: ".modal-dialog",
        },
        {
            trigger: "input[name='model_name']",
            run: "edit new model",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .confirm_button",
            run: "click",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .modal-body #use_stages",
            run: "check",
        },
        {
            trigger: ".modal:not(.o_inactive_modal) .o_web_studio_model_configurator_next",
            run: "click",
        },
        {
            content: "Wait the modal is closed before continue",
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: ".o_web_studio_leave",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: "input#x_name_0",
            run: "edit new record",
        },
        {
            trigger: ".o_arrow_button:contains(In Progress)",
            run: "click",
        },
        {
            trigger: ".o_arrow_button_current:contains(In Progress)",
        },
        {
            trigger: ".o_form_button_save:not(:visible)",
            run: "click",
        },
        {
            // trigger: ".o_back_button", TODO: add breacrumb to access multi-record view when closing studio
            trigger: ".o_nav_entry:contains(new model)",
            run: "click",
        },
        {
            trigger:
                ".o_kanban_group:contains(In Progress) div[name=studio_auto_kanban_header] span.h5:contains(new record)",
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("web_studio_test_enter_x2many_edition_with_multiple_subviews", {
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
                run: "click",
            },
            {
                trigger: ".o_form_view span:contains('Address Type')",
            },
            {
                trigger: ".o_web_studio_navbar_item button:enabled",
                run: "click",
            },
            {
                trigger: ".o_list_renderer span:contains('Address Type')",
            },
            {
                trigger:
                    ".o_web_studio_form_view_editor .o_field_widget[name='child_ids'] .o_field_x2many_list",
                run: "click",
            },
            {
                trigger: ".o-web-studio-edit-x2manys-buttons",
            },
            {
                trigger: ".o_web_studio_editX2Many[data-type='list']",
                run: "click",
            },
            {
                trigger: ".o_content > .o_list_renderer span:contains('Address Type')",
            },
        ],
    });

registry
    .category("web_tour.tours")
    .add("web_studio_test_enter_x2many_edition_with_multiple_subviews_correct_xpath", {
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
                run: "click",
            },
            {
                trigger: ".o_form_view",
            },
            {
                trigger: ".o_web_studio_navbar_item button:enabled",
                run: "click",
            },
            {
                trigger:
                    ".o_web_studio_form_view_editor .o_field_widget[name='child_ids'] .o_field_x2many_list",
                run: "click",
            },
            {
                trigger: ".o-web-studio-edit-x2manys-buttons",
            },
            {
                trigger: ".o_web_studio_editX2Many[data-type='list']",
                run: "click",
            },
            {
                trigger: ".o_view_controller.o_list_view.test-subview-list",
            },
            {
                trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
                run: "click",
            },
            {
                trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_section",
            },
            {
                trigger: `.o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component[data-drop='${JSON.stringify(
                    { fieldName: "active" }
                )}']`,
                run: "drag_and_drop(.o_web_studio_hook:eq(0))",
            },
            {
                content: "Check that the active field has been added",
                trigger: ".o_web_studio_view_renderer .o_list_view thead th[data-name='active']",
            },
        ],
    });

registry.category("web_tour.tours").add("web_studio_test_studio_view_is_last", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run() {
                queryFirst(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)"
                ).scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_inner_group .o_web_studio_hook:last)",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='website']:not(:visible)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_edit_form_subview_attributes", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor .o_field_widget[name='child_ids'] .o_field_x2many_list",
            run: "click",
        },
        {
            trigger: ".o-web-studio-edit-x2manys-buttons",
        },
        {
            trigger: ".o_web_studio_editX2Many[data-type='form']",
            run: "click",
        },
        {
            trigger: ".o_view_controller.o_form_view.test-subview-form",
        },
        {
            trigger: ".o_web_studio_sidebar.o_notebook .nav-link:contains(View)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='create']:checked",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='create']:not(:checked)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_x2many_two_levels_edition", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='user_ids']",
            run: "click",
        },
        {
            trigger: ".o-web-studio-edit-x2manys-buttons",
        },
        {
            trigger: ".o_web_studio_editX2Many[data-type='form']",
            run: "click",
        },
        {
            trigger: ".o_view_controller.o_form_view.test-subview-form-1",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='log_ids']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editX2Many[data-type='form']",
            run: "click",
        },
        {
            trigger: ".o_view_controller.o_form_view.test-subview-form-2",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: ".o_web_studio_existing_fields",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Created on)",
            run: "drag_and_drop .o_web_studio_hook",
        },
        {
            trigger: ".o_web_studio_form_view_editor [data-field-name='create_date']",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_field_group_studio_no_fetch", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
            run() {
                assertEqual(this.anchor.querySelectorAll(".o_field_widget").length, 1);
                assertEqual(
                    this.anchor.querySelectorAll(".o_field_widget")[0].dataset.studioXpath,
                    "/form[1]/field[2]"
                );
            },
        },
        {
            trigger: ".o_web_studio_views_icons a[title='List']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_list_view_editor",
            run() {
                assertEqual(this.anchor.querySelectorAll("th:not(.o_web_studio_hook)").length, 1);
                assertEqual(
                    this.anchor.querySelectorAll("th:not(.o_web_studio_hook)")[0].dataset
                        .studioXpath,
                    "/list[1]/field[2]"
                );
            },
        },
        {
            trigger: ".o_web_studio_views_icons a[title='Kanban']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_kanban_view_editor",
            run() {
                assertEqual(
                    this.anchor.querySelectorAll(
                        ".o_kanban_record:not(.o_kanban_demo):not(.o_kanban_ghost) .o-web-studio-editor--element-clickable"
                    ).length,
                    1
                );
                assertEqual(
                    this.anchor
                        .querySelectorAll(
                            ".o_kanban_record:not(.o_kanban_demo):not(.o_kanban_ghost) .o-web-studio-editor--element-clickable"
                        )[0]
                        .getAttribute("studioxpath"),
                    "/kanban[1]/t[1]/field[2]"
                );
            },
        },
        {
            trigger: ".o_web_studio_views_icons a[title='Calendar']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer .o_calendar_view",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_move_similar_field", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_notebook_headers a:contains('two')",
            run: "click",
        },
        {
            trigger: ".tab-pane.active [data-field-name=display_name]",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))",
        },
        {
            trigger: ".o_web_studio_leave",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_related_file", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_user_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            content: "second",
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_web_studio_field_related",
            run: "drag_and_drop(.o_inner_group)",
        },
        {
            trigger: ".modal-dialog",
        },
        {
            trigger: ".o_model_field_selector_value",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover",
        },
        {
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit Related Partner",
        },
        {
            trigger: "[data-name=partner_id] > button.o_model_field_selector_popover_item_relation",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover_title:contains(Related Partner)",
        },
        {
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit New File",
        },
        {
            trigger:
                ".o_model_field_selector_popover_item_name:contains(New File):not(:contains(filename))",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn-primary:first",
            run: "click",
        },
        {
            trigger: ".o_web_studio_leave",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_undo_new_field", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_integer",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))",
        },
        {
            trigger: "button.o_web_studio_undo.o_web_studio_active",
            run: "click",
        },
        {
            trigger: ".o_web_studio_leave",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_change_lone_attr_modifier_form", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_field_widget[name='name']",
            run: "click",
        },
        {
            trigger: `.o_web_studio_sidebar input[name="required"]`,
        },
        {
            trigger: ".o_web_studio_sidebar",
            run() {
                const required = this.anchor.querySelector(`input[name="required"]`);
                assertEqual(required.checked, true);
            },
        },
        {
            trigger: '.o_web_studio_sidebar input[name="required"]',
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor:not(:has(.o_required_modifier))",
        },
        {
            trigger: ".o_web_studio_sidebar",
            run() {
                const required = this.anchor.querySelector(`input[name="required"]`);
                assertEqual(required.checked, false);
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_new_field_rename_description", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_component.o_web_studio_field_char",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='string']",
            run: "edit my new field && click body",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor label[for='x_studio_my_new_field_0']:contains(my new field)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_edit_digits_option", {
    url: "/odoo",
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },

        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer",
        },
        {
            trigger: "[name=partner_latitude]",
            run: "click",
        },
        {
            trigger: "input#digits",
            run: "edit 2 && click body",
        },
        {
            trigger: ".o_web_studio_leave",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_no_fetch_subview", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: "input#name_0",
            run: "edit value",
        },
        {
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_many2many",
            run: "drag_and_drop(.o_web_studio_form_view_editor .o_web_studio_hook:eq(0))",
        },
        {
            trigger: ".o_record_selector input",
            run: "edit Contact",
        },
        {
            trigger: "a.dropdown-item:contains(Contact)",
            run: "click",
        },
        {
            trigger: ".modal-footer button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_wrap_field label:contains('New Many2Many')",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_button_rainbow_effect", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: `.o_web_studio_view_renderer button[name="open_commercial_entity"]`,
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar #effect",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar #rainbow_message",
        },
        {
            trigger: ".o_web_studio_sidebar",
            run() {
                const blob = new Blob(
                    [
                        "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAIAAAD91JpzAAAAF0lEQVR4nGJxKFrEwMDAxAAGgAAAAP//D+IBWx9K7TUAAAAASUVORK5CYII=",
                    ],
                    { type: "image/png" }
                );
                const file = new File([blob], "my_studio_image.png");

                const fileInput = document.querySelector(
                    ".o_web_studio_sidebar .o_file_input input"
                );
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(file);
                fileInput.files = dataTransfer.files;
                fileInput.dispatchEvent(new Event("change"));
            },
        },
        {
            trigger: ".o_web_studio_sidebar img[src^='/web/content']",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_res_users_fake_fields", {
    steps: () => [
        {
            trigger: ".o_web_studio_existing_fields_header",
            run: "click",
        },
        {
            trigger: ".o_web_studio_existing_fields",
            run() {
                const elements = [...document.querySelectorAll(".o_web_studio_component")];
                const fieldStrings = elements.map((el) => el.innerText.split("\n")[0]);
                assertEqual(fieldStrings.includes("Administration"), false);
                assertEqual(fieldStrings.includes("Multi Companies"), false);
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_reload_after_restoring_default_view", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='name']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='string']",
            run: "edit new name",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_restore",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_undo:not(.o_web_studio_active)",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor .o_field_widget[name='name'] span:contains('Name')",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_edit_reified_field", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor .o_field_widget[name^='sel_groups_'],.o_web_studio_form_view_editor .o_field_widget[name^='in_groups_']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='string']",
            run: "edit new name && click body",
        },
        {
            trigger: ".o_web_studio_leave",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_add_all_types_fields_related", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_user_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
        },
        {
            trigger: ".o_web_studio_field_related",
            run: "drag_and_drop(.o_inner_group)",
        },
        {
            trigger: ".modal-dialog",
        },
        {
            trigger: ".o_model_field_selector_value",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover",
        },
        {
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit Display Name",
        },
        {
            trigger: ".o_model_field_selector_popover_item_name:contains(Display Name)",
            run: "click",
        },
        {
            trigger: ".modal-footer .btn-primary:first",
            run: "click",
        },
        {
            trigger: ".o_web_studio_leave",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_add_one2many_no_related_many2one", {
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
        },
        {
            trigger: ".o_app[data-menu-xmlid='web_studio.studio_app_menu']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_field_one2many",
            run: "drag_and_drop .o_web_studio_form_view_editor .o_inner_group",
        },
        {
            trigger: "h4.modal-title",
            run() {
                assertEqual(this.anchor.textContent, "No related many2one fields found");
            },
        },
        {
            trigger: ".modal-footer .btn.btn-primary",
            run: "click",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_approval_button_xml_id", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor button[name='base.action_model_data']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar [name='create_approval_rule']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer .o_web_studio_approval_avatar",
        },
        {
            trigger: ".o_web_studio_sidebar .o_approval_group #approval_group_id",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_kanban_field_bold", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_kanban_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        // first field has class fw-bold
        {
            trigger:
                ".o_web_studio_view_renderer .o_kanban_record .o-web-studio-editor--element-clickable",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property input#class:value(fs-6 fw-bold whatever)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property input[type=checkbox]#bold:checked",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_property input[type=checkbox]#bold",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property input#class:value(fs-6 whatever)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property input[type=checkbox]#bold:not(:checked)",
        },
        // second field has class fw-bolder
        {
            trigger:
                ".o_web_studio_view_renderer .o_kanban_record .o-web-studio-editor--element-clickable:eq(1)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_property input#class:value(fw-bolder)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property input[type=checkbox]#bold:checked",
        },
        // third field isn't bold
        {
            trigger:
                ".o_web_studio_view_renderer .o_kanban_record .o-web-studio-editor--element-clickable:eq(2)",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_property input#class:value(text-muted)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property input[type=checkbox]#bold:not(:checked)",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_property input[type=checkbox]#bold",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_property input#class:value(fw-bold)",
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_property input[type=checkbox]#bold:checked",
        },
    ],
});

async function animationFrame(timeoutBefore) {
    await new Promise((resolve) => setTimeout(resolve, timeoutBefore));
    await new Promise(requestAnimationFrame);
}

registry.category("web_tour.tours").add("web_studio_test_kanban_menu_ribbon", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_kanban_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer .o_kanban_view",
        },
        {
            trigger: ".nav .o_web_studio_new",
            run: "click",
        },
        {
            trigger: ".nav .o_web_studio_new.active",
            run() {
                return waitFor(".o_web_studio_component.o_web_studio_field_menu", {
                    timeout: 3000,
                });
            },
        },
        {
            trigger: ".o_web_studio_view_renderer .o_web_studio_hook[data-type='t']",
        },
        {
            trigger: ".o_web_studio_component.o_web_studio_field_menu",
            async run() {
                await animationFrame();
                const { drop, moveTo } = await drag(this.anchor);
                await moveTo(".o_kanban_record:first");
                await animationFrame(500); // wait for animations to finish in under 500ms
                const target = await waitFor(".o_web_studio_hook_visible", {
                    visible: true,
                    timeout: 5000,
                });
                await moveTo(target, { interactive: false });
                await drop();
            },
        },
        {
            trigger: ".o_kanban_view .o_kanban_record:first() .o_dropdown_kanban",
        },
        {
            trigger: ".o_web_studio_component.o_web_studio_field_ribbon",
            run: "drag_and_drop(.o_web_studio_hook[data-type='ribbon'])",
        },
        {
            trigger:
                ".o_kanban_view .o_kanban_record:first() .o_widget_web_ribbon .ribbon:contains(demo)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_related", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer .o_form_view",
        },
        {
            trigger: ".o_web_studio_component.o_web_studio_field_related",
            run: "drag_and_drop (.o_web_studio_hook:last())",
        },
        {
            trigger: ".modal .o_model_field_selector_value",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit Related Company",
        },
        {
            trigger:
                ".o_model_field_selector_popover_item[data-name='parent_id'] .o_model_field_selector_popover_relation_icon",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover_title:contains(Related Company)",
        },
        {
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit Contact",
        },
        {
            trigger:
                ".o_model_field_selector_popover_item[data-name='child_ids'] .o_model_field_selector_popover_item_name",
            run: "click",
        },
        {
            trigger: ".modal footer button.btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer .o_field_widget.o_field_one2many",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_negated_groups", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input#show_invisible",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_sidebar [name='negated_groups_id'] .o_badge:contains(studio has group)",
        },
        {
            trigger: ".o_web_studio_sidebar [name='negated_groups_id'] .o_delete",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_sidebar [name='negated_groups_id']:not(:contains(studio has group))",
        },
        {
            trigger: ".o_web_studio_sidebar [name='negated_groups_id'] input",
            run: "edit Access Rights",
        },
        {
            trigger: "a.dropdown-item:contains(Administration / Access Rights)",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_sidebar [name='negated_groups_id'] .o_badge:contains(Administration / Access Rights)",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_use_action_domain", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_list_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar",
        },
        {
            trigger: ".o_list_table",
            run() {
                const names = Array.from(
                    document.querySelectorAll(".o_list_table td[name=display_name]")
                ).map((e) => e.textContent);
                if (names.length !== 1 || names[0] !== "Michel") {
                    throw new Error("record with employee=false should not be matched");
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_drag_before_sheet", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_html",
            run: "drag_and_drop (.o_web_studio_form_view_editor .o_web_studio_hook:eq(0))",
        },
        {
            trigger: "button.o_web_studio_undo.o_web_studio_active",
            run() {},
        },
        {
            trigger: ".o_web_studio_leave",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_default_value_company", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
            run: "click",
        },
        {
            trigger: ".o_web_studio_view_renderer .o_form_view .o_field_widget[name='name']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[id='default_value']",
            async run(helpers) {
                // in this flow, only the input's value is changing
                // We want to wait for the RPC to return. That will
                // "commit" the value in the input.
                // Since when the value of an input changes, there are no DOM
                // mutations, we need to use the waitFor from Hoot
                // instead of the macro.js machinery to assert that the value has changed
                // as a consequence of the RPC
                this.anchor.scrollIntoView();
                const cb = ({ detail }) => {
                    if (detail.url === "/web_studio/set_default_value") {
                        this.anchor.value = "";
                        rpcBus.removeEventListener("RPC:REQUEST", cb);
                    }
                };
                rpcBus.addEventListener("RPC:REQUEST", cb);
                await helpers.edit("from studio");
                await helpers.press("ENTER");
                return waitFor(
                    ".o_web_studio_sidebar input[id='default_value']:value(from studio)",
                    { timeout: 5000 }
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_subview_multiple_occurences", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view .o_form_editable",
            run: "click",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
            run: "click",
        },
        {
            trigger: ".o_web_studio_form_view_editor div[name='child_ids']",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor div[name='child_ids'] .o_web_studio_editX2Many[data-type='list']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='function']",
            run() {
                assertEqual(
                    Array.from(document.querySelectorAll("th[data-name='function']")).length,
                    1
                );
            },
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='function']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='string']",
            run: "edit new label from tour && click body",
        },
        {
            trigger: ".o_web_studio_snackbar .fa-check",
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_negated_groups_do_not_interfere_with_invisible", {
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button:enabled",
            run: "click",
        },
        {
            trigger:
                ".o_in_studio .o_form_view:has([data-field-name=name]):not(:has([data-field-name=function])",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input#show_invisible",
            run: "click",
        },
        {
            content: "Click on the function field",
            trigger: ".o_web_studio_form_view_editor .o-web-studio-editor--element-clickable:eq(2)",
            run: "click",
        },
        {
            content: "The invisible checkbox should not be checked",
            trigger: ".o_web_studio_property #invisible:not(:checked)",
        },
        {
            trigger: ".o_web_studio_attrs[data-type=invisible]",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_value",
            run: "click",
        },
        {
            trigger: ".o_model_field_selector_popover_item_name:contains('Display Name')",
            run: "click",
        },
        {
            trigger: ".o_tree_editor_condition input.o_input",
            run: "edit Robert && click body",
        },
        {
            trigger: ".modal-footer .btn-primary",
            run: "click",
        },
        {
            trigger: ".o_web_studio_property .o_web_studio_checkbox_indeterminate #invisible",
        },
        {
            trigger: ".o_web_studio_leave",
            run: "click",
        },
        ...stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_automagically_added_fields", {
    steps: () => [
        {
            trigger: ".o_list_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editor_manager .o_list_view",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='show_invisible']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editor_manager .o_list_view .o_web_studio_show_invisible",
            run: () => {
                const allTh = document.querySelectorAll(".o_list_view th:not(.o_web_studio_hook)");
                assertEqual([...allTh].map((th) => th.textContent).toString(), "Display Name,Name");
            },
        },
        {
            trigger: ".o_web_studio_views_icons a[title='Kanban']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editor_manager .o_kanban_view",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='show_invisible']",
            run: "click",
        },
        {
            trigger:
                ".o_web_studio_editor_manager .o_kanban_record:has(.o_web_studio_show_invisible)",
            run() {
                const allInvisible = [...document.querySelectorAll(".o_web_studio_show_invisible")];
                assertEqual(allInvisible.length, 2);
                assertEqual(
                    allInvisible.map((el) => el.getAttribute("name")).toString(),
                    "display_name,name"
                );
            },
        },
        {
            trigger: ".o_web_studio_views_icons a[title='Form']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editor_manager .o_form_view",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
            run: "click",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='show_invisible']",
            run: "click",
        },
        {
            trigger: ".o_web_studio_editor_manager .o_form_view:has(.o_web_studio_show_invisible)",
            run() {
                const allInvisible = [...document.querySelectorAll(".o_field_widget")];
                assertEqual(allInvisible.length, 2);
                assertEqual(
                    allInvisible.map((el) => el.getAttribute("name")).toString(),
                    "display_name,name"
                );
            },
        },
    ],
});
