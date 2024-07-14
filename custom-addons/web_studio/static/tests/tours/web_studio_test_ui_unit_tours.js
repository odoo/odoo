/** @odoo-module */
import { registry } from "@web/core/registry";
import { stepNotInStudio, assertEqual } from "@web_studio/../tests/tours/tour_helpers";

registry
    .category("web_tour.tours")
    .add("web_studio_test_form_view_not_altered_by_studio_xml_edition", {
        test: true,
        url: "/web?debug=1",
        sequence: 260,
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            },
            {
                trigger: ".o_form_view .o_form_editable",
            },
            {
                trigger: ".o_web_studio_navbar_item button",
            },
            {
                trigger: ".o_web_studio_sidebar .o_web_studio_view",
            },
            {
                trigger: ".o_web_studio_open_xml_editor",
            },
            {
                extra_trigger: ".o_web_studio_code_editor_info",
                trigger: ".o_web_studio_leave",
            },
            stepNotInStudio(".o_form_view .o_form_editable"),
        ],
    });

/* global ace */
registry.category("web_tour.tours").add("web_studio_test_edit_with_xml_editor", {
    test: true,
    url: "/web?debug=1",
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".someDiv",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
        },
        {
            trigger: ".o_web_studio_open_xml_editor",
        },
        {
            extra_trigger: ".o_web_studio_xml_editor",
            trigger: ".o_web_studio_xml_resource_selector .o_select_menu_toggler",
        },
        {
            trigger:
                ".o_web_studio_xml_resource_selector .o-dropdown--menu .o_select_menu_item:contains(Odoo Studio)",
        },
        {
            trigger: ".ace_content",
            run() {
                ace.edit(document.querySelector(".ace_editor")).setValue("<data/>");
            },
        },
        {
            trigger: ".o_web_studio_xml_editor .o_web_studio_xml_resource_selector .btn-primary",
        },
        {
            trigger: ".o_web_studio_snackbar:not(:has(.fa-spin))",
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
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='user_ids']",
        },
        {
            extra_trigger: ".o-web-studio-edit-x2manys-buttons",
            trigger: ".o_web_studio_editX2Many[data-type='form']",
        },
        {
            extra_trigger: ".o_view_controller.o_form_view.test-user-form",
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
        },
        {
            extra_trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run() {
                $(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)"
                )[0].scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))",
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
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor .o_field_widget[name='user_ids'] .o_field_x2many_list",
        },
        {
            extra_trigger: ".o-web-studio-edit-x2manys-buttons",
            trigger: ".o_web_studio_editX2Many[data-type='list']",
        },
        {
            extra_trigger: ".o_view_controller.o_list_view.test-user-list",
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
        },
        {
            extra_trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run() {
                $(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)"
                )[0].scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
            run: "drag_and_drop_native (.o_web_studio_list_view_editor .o_web_studio_hook:eq(1))",
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
        test: true,
        sequence: 260,
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            },
            {
                trigger: ".o_form_view .o_form_editable",
            },
            {
                trigger: ".o_web_studio_navbar_item button",
            },
            {
                trigger:
                    ".o_web_studio_form_view_editor .o_field_widget[name='user_ids']:eq(1) .o_field_x2many_list",
            },
            {
                extra_trigger: ".o-web-studio-edit-x2manys-buttons",
                trigger: ".o_web_studio_editX2Many[data-type='list']",
            },
            {
                extra_trigger: ".o_view_controller.o_list_view.test-user-list",
                trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            },
            {
                extra_trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
                trigger:
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
                run() {
                    $(
                        ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)"
                    )[0].scrollIntoView();
                },
            },
            {
                trigger:
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(User log entries)",
                run: "drag_and_drop_native (.o_web_studio_list_view_editor .o_web_studio_hook:eq(1))",
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

registry.category("web_tour.tours").add(
    "web_studio_boolean_field_drag_and_drop",
    {
        test: true,
        sequence: 260,
        steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']"
        },
        {
            trigger: ".o_form_view .o_form_editable"
        },
        {
            trigger: ".o_web_studio_navbar_item button"
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_boolean",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_web_studio_hook:eq(0))",
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor",
            trigger: ".o_wrap_field_boolean .o_wrap_label",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_web_studio_hook:eq(2))",
        },
        {
            trigger: ".o_wrap_label:eq(1):contains('New CheckBox')",
            run() {}
        },
    ]
});

registry.category("web_tour.tours").add("web_studio_field_with_group", {
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_list_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='function']",
            run() {},
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
        },
        {
            extra_trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run() {
                $(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)"
                )[0].scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run: "drag_and_drop_native (.o_web_studio_list_view_editor th.o_web_studio_hook:eq(2))",
        },
        {
            extra_trigger:
                ".o_web_studio_list_view_editor th.o_web_studio_hook:not(.o_web_studio_nearest_hook)",
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
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
            extra_trigger: ".o_list_view",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='title']",
        },
        {
            trigger: ".o_web_studio_sidebar_checkbox:nth-child(1) .o_web_studio_attrs",
        },
        {
            trigger: ".o_model_field_selector_value",
        },
        {
            trigger: ".o_model_field_selector_popover_item_name:contains('Display Name')",
            in_modal: false,
        },
        {
            trigger: ".o_tree_editor_condition input.o_input",
            run: "text Robert",
        },
        {
            trigger: ".modal-footer .btn-primary",
        },
        {
            trigger: ".o_web_studio_list_view_editor th[data-name='title']",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_elements_with_groups_form", {
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
            run() {},
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
        },
        {
            extra_trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run() {
                $(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)"
                )[0].scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_inner_group .o_web_studio_hook:eq(1))",
        },
        {
            extra_trigger:
                ".o_web_studio_form_view_editor .o_web_studio_hook:not(.o_web_studio_nearest_hook)",
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='website']",
            allowInvisible: true,
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
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor .o_field_widget[name='display_name']",
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='display_name']",
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
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_selection",
            run: "drag_and_drop_native (.o_web_studio_hook:eq(0))",
        },
        {
            trigger: ".o_web_studio_add_selection .o-web-studio-interactive-list-item-input",
            run: "text some value",
        },
        {
            trigger: ".modal-footer .btn-primary",
        },
        {
            extra_trigger: "body:not(:has(.modal))",
            trigger: ".o_web_studio_leave",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_wrap_input:has(.o_field_selection)",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_edit_selection_values",
        },
        {
            in_modal: true,
            trigger: ".o_web_studio_add_selection .o-web-studio-interactive-list-item-input",
            run: "text another value cancel",
        },
        {
            trigger: ".o_web_studio_add_selection .o-web-studio-interactive-list-edit-item",
        },
        {
            trigger: ".o_web_studio_selection_editor li:nth-child(2)",
            async run() {
                assertEqual(this.$anchor[0].textContent, "another value cancel");
            },
        },
        {
            trigger: ".modal-footer .btn-secondary",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_edit_selection_values",
        },
        {
            trigger: ".o_web_studio_selection_editor li",
            run() {
                assertEqual(
                    Array.from(this.$anchor)
                        .map((el) => el.textContent)
                        .join(" "),
                    "some value"
                );
            },
        },
        {
            in_modal: true,
            trigger: ".o_web_studio_add_selection .o-web-studio-interactive-list-item-input",
            run: "text another value",
        },
        {
            trigger: ".modal-footer .btn-primary",
        },
        {
            extra_trigger: "body:not(:has(.modal))",
            trigger: ".o_web_studio_leave",
        },
        stepNotInStudio(),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_one2many_lines_then_edit_name", {
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_lines",
            run: "drag_and_drop_native (.o_web_studio_hook:eq(0))",
        },
        {
            trigger: ".o_form_label",
            extra_trigger: ".o_field_x2many_list",
            timeout: 20000,
        },
        {
            extra_trigger: ".o_web_studio_sidebar .o_web_studio_properties.active",
            trigger: "input[name='string']",
            run: "text new name",
        },
        {
            trigger: ".o_web_studio_leave",
            timeout: 20000,
        },
        stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_address_view_id_no_edit", {
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_address_format",
            run: function () {
                if (
                    this.$anchor.find("[name=lang]").length ||
                    !this.$anchor.find("[name=street]").length
                ) {
                    throw new Error(
                        "The address view id set on the company country should be displayed"
                    );
                }
            },
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            extra_trigger: ".o_web_studio_view_renderer",
            trigger: ".o_address_format",
            run: function () {
                if (
                    this.$anchor.find("[name=street]").length ||
                    !this.$anchor.find("[name=lang]").length
                ) {
                    throw new Error(
                        "The address view id set on the company country shouldn't be editable"
                    );
                }
            },
        },
        {
            trigger: ".o_web_studio_leave",
        },
        stepNotInStudio(".o_form_view"),
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_new_model_from_existing_view", {
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_kanban_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_create_new_model",
        },
        {
            extra_trigger: ".modal-dialog",
            trigger: "input[name='model_name']",
            run: "text new model",
        },
        {
            trigger: ".confirm_button",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            trigger: ".o_form_view",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_create_model_with_clickable_stages", {
    test: true,
    sequence: 260,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_create_new_model",
        },
        {
            extra_trigger: ".modal-dialog",
            trigger: "input[name='model_name']",
            run: "text new model",
        },
        {
            trigger: ".confirm_button",
        },
        {
            trigger: "#use_stages",
        },
        {
            trigger: ".o_web_studio_model_configurator_next",
        },
        {
            trigger: ".o_web_studio_leave",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: "input#x_name_0",
            run: "text new record",
        },
        {
            trigger: ".o_arrow_button:contains(In Progress)",
        },
        {
            extra_trigger: ".o_arrow_button_current:contains(In Progress)",
            trigger: ".o_form_button_save",
        },
        {
            trigger: ".o_back_button",
        },
        {
            trigger:
                ".o_kanban_group:contains(In Progress) .o_kanban_record_details:contains(new record)",
            isCheck: true,
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("web_studio_test_enter_x2many_edition_with_multiple_subviews", {
        test: true,
        sequence: 260,
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            },
            {
                extra_trigger: ".o_form_view span:contains('Address Type')",
                trigger: ".o_web_studio_navbar_item button",
            },
            {
                trigger:
                    ".o_web_studio_form_view_editor .o_field_widget[name='child_ids'] .o_field_x2many_list",
                extra_trigger: ".o_list_renderer span:contains('Address Type')",
            },
            {
                extra_trigger: ".o-web-studio-edit-x2manys-buttons",
                trigger: ".o_web_studio_editX2Many[data-type='list']",
            },
            {
                trigger: ".o_content > .o_list_renderer span:contains('Address Type')",
                isCheck: true,
            },
        ],
    });

registry
    .category("web_tour.tours")
    .add("web_studio_test_enter_x2many_edition_with_multiple_subviews_correct_xpath", {
        test: true,
        sequence: 260,
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            },
            {
                extra_trigger: ".o_form_view",
                trigger: ".o_web_studio_navbar_item button",
            },
            {
                trigger:
                    ".o_web_studio_form_view_editor .o_field_widget[name='child_ids'] .o_field_x2many_list",
            },
            {
                extra_trigger: ".o-web-studio-edit-x2manys-buttons",
                trigger: ".o_web_studio_editX2Many[data-type='list']",
            },
            {
                extra_trigger: ".o_view_controller.o_list_view.test-subview-list",
                trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
            },
            {
                extra_trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_section",
                trigger: `.o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component[data-drop='${JSON.stringify(
                    { fieldName: "active" }
                )}']`,
                run: "drag_and_drop_native (.o_web_studio_hook:eq(0))",
            },
            {
                content: "Check that the active field has been added",
                trigger: ".o_web_studio_view_renderer .o_list_view thead th[data-name='active']",
                isCheck: true,
            },
        ],
    });

registry.category("web_tour.tours").add("web_studio_test_studio_view_is_last", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
        },
        {
            extra_trigger: ".o_web_studio_existing_fields_section:not(.d-none)",
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run() {
                $(
                    ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)"
                )[0].scrollIntoView();
            },
        },
        {
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Website Link)",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_inner_group .o_web_studio_hook:last)",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='website']",
            allowInvisible: true,
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_edit_form_subview_attributes", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger:
                ".o_web_studio_form_view_editor .o_field_widget[name='child_ids'] .o_field_x2many_list",
        },
        {
            extra_trigger: ".o-web-studio-edit-x2manys-buttons",
            trigger: ".o_web_studio_editX2Many[data-type='form']",
        },
        {
            extra_trigger: ".o_view_controller.o_form_view.test-subview-form",
            trigger: ".o_web_studio_sidebar.o_notebook .nav-link:contains(View)",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='create']:checked",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='create']:not(:checked)",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_x2many_two_levels_edition", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='user_ids']",
        },
        {
            extra_trigger: ".o-web-studio-edit-x2manys-buttons",
            trigger: ".o_web_studio_editX2Many[data-type='form']",
        },
        {
            extra_trigger: ".o_view_controller.o_form_view.test-subview-form-1",
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='log_ids']",
        },
        {
            trigger: ".o_web_studio_editX2Many[data-type='form']",
        },
        {
            trigger: ".o_view_controller.o_form_view.test-subview-form-2",
            run() {},
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_existing_fields_header",
        },
        {
            extra_trigger: ".o_web_studio_existing_fields",
            trigger:
                ".o_web_studio_sidebar .o_web_studio_existing_fields_section .o_web_studio_component:contains(Created on)",
            run: "drag_and_drop_native .o_web_studio_hook",
        },
        {
            trigger: ".o_web_studio_form_view_editor [data-field-name='create_date']",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_field_group_studio_no_fetch", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_form_view_editor",
            run() {
                assertEqual(this.$anchor[0].querySelectorAll(".o_field_widget").length, 1);
                assertEqual(
                    this.$anchor[0].querySelectorAll(".o_field_widget")[0].dataset.studioXpath,
                    "/form[1]/field[2]"
                );
            },
        },
        {
            trigger: ".o_web_studio_views_icons a[title='List']",
        },
        {
            trigger: ".o_web_studio_list_view_editor",
            run() {
                assertEqual(
                    this.$anchor[0].querySelectorAll("th:not(.o_web_studio_hook)").length,
                    1
                );
                assertEqual(
                    this.$anchor[0].querySelectorAll("th:not(.o_web_studio_hook)")[0].dataset
                        .studioXpath,
                    "/tree[1]/field[2]"
                );
            },
        },
        {
            trigger: ".o_web_studio_views_icons a[title='Kanban']",
        },
        {
            trigger: ".o_web_studio_kanban_view_editor",
            run() {
                assertEqual(
                    this.$anchor[0].querySelectorAll(
                        ".o_kanban_record:not(.o_kanban_demo):not(.o_kanban_ghost) [data-field-name]"
                    ).length,
                    1
                );
                assertEqual(
                    this.$anchor[0]
                        .querySelectorAll(
                            ".o_kanban_record:not(.o_kanban_demo):not(.o_kanban_ghost) [data-field-name]"
                        )[0]
                        .getAttribute("studioxpath"),
                    "/kanban[1]/t[1]/field[2]"
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_move_similar_field", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor",
            trigger: ".o_notebook_headers a:contains('two')",
        },
        {
            trigger: ".tab-pane.active [data-field-name=display_name]",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))",
        },
        {
            trigger: ".o_web_studio_leave",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_related_file", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_user_menu']",
        },
        {
            content: "second",
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor",
            trigger: ".o_web_studio_field_related",
            run: "drag_and_drop_native (.o_inner_group)",
        },
        {
            extra_trigger: ".modal-dialog",
            trigger: ".o_model_field_selector_value",
        },
        {
            in_modal: false,
            extra_trigger: ".o_model_field_selector_popover",
            trigger: ".o_model_field_selector_popover_search input",
            run: "text Related Partner",
        },
        {
            in_modal: false,
            trigger: "[data-name=partner_id] > button.o_model_field_selector_popover_item_relation",
        },
        {
            in_modal: false,
            trigger: ".o_model_field_selector_popover_search input",
            run: "text New File",
        },
        {
            in_modal: false,
            trigger:
                ".o_model_field_selector_popover_item_name:contains(New File):not(:contains(filename))",
        },
        {
            trigger: ".modal-footer .btn-primary:first",
        },
        {
            trigger: ".o_web_studio_leave",
            run() {},
        },
    ],
});

registry.category("web_tour.tours").add("web_studio_test_undo_new_field", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_integer",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))",
        },
        {
            trigger: "button.o_web_studio_undo.o_web_studio_active",
        },
        {
            trigger: ".o_web_studio_leave",
            isCheck: true,
        }
    ]
});

registry.category("web_tour.tours").add("web_studio_test_change_lone_attr_modifier_form", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor",
            trigger: ".o_field_widget[name='name']",
        },
        {
            extra_trigger: `.o_web_studio_sidebar input[name="required"]`,
            trigger: '.o_web_studio_sidebar',
            run() {
                const required = this.$anchor[0].querySelector(`input[name="required"]`);
                assertEqual(required.checked, true);
            }
        },
        {
            trigger: '.o_web_studio_sidebar input[name="required"]',
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor:not(:has(.o_required_modifier))",
            trigger: '.o_web_studio_sidebar',
            run() {
                const required = this.$anchor[0].querySelector(`input[name="required"]`);
                assertEqual(required.checked, false);
            }
        }
    ]
});

registry.category("web_tour.tours").add("web_studio_test_new_field_rename_description", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            extra_trigger: ".o_web_studio_form_view_editor",
            trigger: ".o_web_studio_sidebar .o_web_studio_component.o_web_studio_field_char",
            run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_web_studio_hook:eq(1))"
        },
        {
            trigger: ".o_web_studio_sidebar input[name='string']",
            run: "text my new field",
        },
        {
            trigger: ".o_web_studio_form_view_editor label[for='x_studio_my_new_field_0']:contains(my new field)",
            isCheck: true,
        }
    ]
});

registry
    .category("web_tour.tours")
    .add("web_studio_test_edit_digits_option", {
        test: true,
        url: "/web",
        sequence: 260,
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            },
            {
                trigger: ".o_form_view .o_form_editable",
            },

            {
                trigger: ".o_web_studio_navbar_item button",
            },
            {
                extra_trigger: ".o_web_studio_view_renderer",
                trigger: "[name=partner_latitude]",
            },
            {
                trigger: "input#digits",
                run: "text 2",
            },
            {
                trigger: ".o_web_studio_leave",
                isCheck: true,
            },
        ],
    });

    registry.category("web_tour.tours").add("web_studio_no_fetch_subview", {
        test: true,
        steps: () => [
            {
                trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
            },
            {
                trigger: "input#name_0",
                run: "text value"
            },
            {
                trigger: "button.o_form_button_save",
            },
            {
                extra_trigger: ".o_form_view",
                trigger: ".o_web_studio_navbar_item button",
            },
            {
                trigger: ".o_web_studio_sidebar .o_web_studio_new_fields .o_web_studio_field_many2many",
                run: "drag_and_drop_native (.o_web_studio_form_view_editor .o_web_studio_hook:eq(0))",
            },
            {
                trigger: ".o_record_selector input",
                run: "text Contact",
            },
            {
                trigger:"a.dropdown-item:contains(Contact)",
            },
            {
                trigger: ".modal-footer button.btn-primary",
            },
            {
                trigger:".o_wrap_field label:contains('New Many2Many')",
                isCheck: true,
            }
        ],
    });

registry.category("web_tour.tours").add("web_studio.test_button_rainbow_effect", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            trigger: ".o_form_view .o_form_editable",
        },
        {
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: `.o_web_studio_view_renderer button[name="open_commercial_entity"]`,
        },
        {
            trigger: ".o_web_studio_sidebar #effect",
        },
        {
            extra_trigger: ".o_web_studio_sidebar #rainbow_message",
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
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("web_studio.test_res_users_fake_fields", {
    test: true,
    steps: () => [
        {
            trigger: ".o_web_studio_existing_fields_header"
        },
        {
            trigger: ".o_web_studio_existing_fields",
            run() {
                const elements = [...document.querySelectorAll(".o_web_studio_component")];
                const fieldStrings = elements.map(el => el.innerText.split("\n")[0]);
                assertEqual(fieldStrings.includes("Administration"), false);
                assertEqual(fieldStrings.includes("Multi Companies"), false);
            }
        }
    ]
});

registry.category("web_tour.tours").add("web_studio_test_reload_after_restoring_default_view", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='name']",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='string']",
            run: "text new name",
        },
        {
            trigger: ".o_web_studio_sidebar .o_web_studio_view",
        },
        {
            trigger: ".o_web_studio_restore"
        },
        {
            trigger: ".modal-footer .btn-primary",
        },
        {
            extra_trigger: ".o_web_studio_undo:not(.o_web_studio_active)",
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name='name'] span:contains('Name')",
            isCheck: true,
        },
    ]
});

registry.category("web_tour.tours").add("web_studio_test_edit_reified_field", {
    test: true,
    steps: () => [
        {
            trigger: "a[data-menu-xmlid='web_studio.studio_test_partner_menu']",
        },
        {
            extra_trigger: ".o_form_view",
            trigger: ".o_web_studio_navbar_item button",
        },
        {
            trigger: ".o_web_studio_form_view_editor .o_field_widget[name^='sel_groups_'],.o_web_studio_form_view_editor .o_field_widget[name^='in_groups_']",
        },
        {
            trigger: ".o_web_studio_sidebar input[name='string']",
            run: "text new name",
        },
        {
            trigger: ".o_web_studio_leave",
            isCheck: true,
        },
    ]
});
