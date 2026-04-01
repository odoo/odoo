import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

function assertEqual(actual, expected) {
    if (actual !== expected) {
        throw new Error(`Assert failed: expected: ${expected} ; got: ${actual}`);
    }
}

registry.category("web_tour.tours").add("test_base_automation", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Create new rule",
            trigger: ".o_control_panel button.o-kanban-button-new",
            run: "click",
        },
        {
            content: "Enter rule name",
            trigger: ".o_form_renderer .oe_title .o_input",
            run: "edit Test rule",
        },
        {
            content: "Select model",
            trigger: '.o_form_renderer .o_group div[name="model_id"] input',
            run: "edit res.partner",
        },
        {
            trigger: ".dropdown-menu:contains(Contact)",
        },
        {
            content: "Select model contact",
            trigger: ".dropdown-menu li a:contains(Contact):not(:has(.fa-spin))",
            run: "click",
        },
        {
            content: "Open select",
            trigger: ".o_form_renderer #trigger_0",
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:contains(On create and edit)",
            run: "click",
        },
        {
            content: "Add new action",
            trigger: '.o_form_renderer div[name="action_server_ids"] button',
            run: "click",
        },
        {
            content: "Set new action to update the record",
            trigger:
                ".modal .modal-content .o_form_renderer [name='state'] span[value*='object_write']",
            run: "click",
        },
        {
            content: "Focus on the 'update_path' field",
            trigger:
                ".modal .modal-content .o_form_renderer [name='update_path'] .o_model_field_selector",
            run: "click",
        },
        {
            content: "Input field name",
            trigger: ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
            run: "edit Job Position",
        },
        {
            content: "Select field",
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_page li[data-name="function"] button',
            run: "click",
        },
        {
            content: "Open update select",
            trigger:
                '.modal .modal-content .o_form_renderer div[name="value"] textarea',
            run: "edit Test",
        },
        {
            content: "Open update select",
            trigger: ".modal .modal-content .o_form_button_save",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        ...stepUtils.saveForm(),
    ],
});

registry.category("web_tour.tours").add("test_base_automation_on_tag_added", {
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_control_panel button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_form_renderer .oe_title .o_input",
            run: "edit Test rule",
        },
        {
            trigger: '.o_form_renderer .o_group div[name="model_id"] input',
            run: "edit test_base_automation.project",
        },
        {
            trigger:
                ".dropdown-menu li a:contains(test_base_automation.project):not(:has(.fa-spin))",
            run: "click",
        },
        {
            content: "Open select",
            trigger: ".o_form_renderer #trigger_0",
            run: "click",
        },
        {
            trigger: ".o_select_menu_menu",
            run() {
                const options = [...this.anchor.querySelectorAll(".o_select_menu_item")].map(
                        (el) => el.textContent
                    );

                assertEqual(
                    JSON.stringify(options),
                    JSON.stringify([
                        "Stage is set to",
                        "User is set",
                        "Tag is added",
                        "Priority is set to",
                        "Based on date field",
                        "After creation",
                        "After last update",
                        "On create",
                        "On create and edit",
                        "On deletion",
                        "On UI change",
                        "On webhook"
                    ])
                );
            },
        },
        {
            trigger: ".o_select_menu_item:contains(Tag is added)",
            run: "click",
        },
        {
            trigger: '.o_form_renderer div[name="trg_field_ref"] input',
            run: "edit test",
        },
        {
            trigger: ".dropdown-menu li a:contains(test):not(:has(.fa-spin))",
            run: "click",
        },
        {
            trigger: '.o_form_renderer div[name="action_server_ids"] button',
            run: "click",
        },
        {
            trigger:
                ".modal .modal-content .o_form_renderer [name='state'] span[value*='object_write']",
            run: "click",
        },
        {
            content: "Focus on the 'update_path' field",
            trigger:
                ".modal .modal-content .o_form_renderer [name='update_path'] .o_model_field_selector",
            run: "click",
        },
        {
            content: "Input field name",
            trigger:
                ".o_model_field_selector_popover .o_model_field_selector_popover_search  input",
            run: "edit Name",
        },
        {
            content: "Select field",
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_page li[data-name="name"] button',
            run: "click",
        },
        {
            trigger:
                '.modal .modal-content .o_form_renderer div[name="value"] textarea',
            run: "edit Test",
        },
        {
            trigger: ".modal .modal-content .o_form_button_save",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal))",
        },
        {
            trigger: '.o_form_renderer div[name="action_server_ids"] button',
            run: "click",
        },
        {
            trigger:
                ".modal .modal-content .o_form_renderer [name='state'] span[value*='object_write']",
            run: "click",
        },
        {
            content: "Focus on the 'update_path' field",
            trigger:
                ".modal .modal-content .o_form_renderer [name='update_path'] .o_model_field_selector",
            run: "click",
        },
        {
            content: "Input field name",
            trigger:
                ".o_model_field_selector_popover .o_model_field_selector_popover_search  input",
            run: "edit Priority",
        },
        {
            content: "Select field",
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_page li[data-name="priority"] button',
            run: "click",
        },
        {
            trigger:
                '.modal .modal-content .o_form_renderer div[name="selection_value"] input',
            run: "edit High",
        },
        {
            trigger: ".dropdown-menu li a:contains(High):not(:has(.fa-spin))",
            run: "click",
        },
        {
            trigger: ".modal .modal-content .o_form_button_save",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal-content))",
        },
        ...stepUtils.saveForm(),
        {
            trigger: ".breadcrumb .o_back_button a",
            run: "click",
        },
        {
            trigger: ".o_base_automation_kanban_view .o_kanban_record",
            run() {
                assertEqual(
                    this.anchor.querySelector(".o_automation_base_info").textContent,
                    "Test ruletest_base_automation.projectTag is addedtest"
                );
                assertEqual(
                    this.anchor.querySelector(".o_automation_actions").textContent,
                    "Update test_base_automation.projectUpdate test_base_automation.project"
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_open_automation_from_grouped_kanban", {
    steps: () => [
        {
            trigger: ".o_kanban_header:contains(test tag)",
            run: "hover && click .o_kanban_view .o_group_config button.dropdown-toggle",
        },
        {
            trigger: ".dropdown-menu .o_column_automations",
            run: "click",
        },
        {
            trigger: ".o_base_automation_kanban_view .o_control_panel button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            run() {
                assertEqual(
                    this.anchor.querySelector(".o_field_widget[name='trigger'] input").value,
                    "Tag is added"
                );
                assertEqual(
                    this.anchor.querySelector(".o_field_widget[name='trg_field_ref'] input").value,
                    "test tag"
                );
            },
        },
        {
            trigger: ".o_form_view .o_field_widget[name='name'] input",
            run: "edit From Tour",
        },
        ...stepUtils.saveForm(),
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_stage_trigger", {
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
        },
        {
            trigger: ".o_kanban_record .fs-2:contains(Test Stage)",
        },
        {
            trigger: ".o_kanban_record .o_tag:contains(Stage value)",
        },
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_time_trigger", {
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
        },
        {
            trigger: ".o_automation_base_info > div > div > span:nth-child(1):contains(1)",
        },
        {
            trigger: ".o_automation_base_info .text-lowercase:contains(hours)",
        },
        {
            trigger: `.o_kanban_record .o_tag:contains("Last Automation (Automated Rule Test)")`,
        },
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_time_updated_trigger", {
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
        },
        {
            trigger: ".o_automation_base_info > div > div > span:nth-child(1):contains(1)",
            async run() {
                const lowercaseTexts = document.querySelectorAll(
                    ".o_automation_base_info .text-lowercase"
                );
                assertEqual(lowercaseTexts.length, 2);
                assertEqual(lowercaseTexts[0].innerText, "hours");
                assertEqual(lowercaseTexts[1].innerText, "after last update");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_create_action", {
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
        },
        {
            trigger: "div[name='action_server_ids']:contains(Create Contact with name NameX)",
            async run() {
                assertEqual(document.querySelectorAll(".fa.fa-plus-square").length, 1);
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_resize_kanban", {
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
        },
        {
            trigger:
                ".o_automation_actions:contains(Set Active To False Set Active To False Set Active To False)",
            async run() {
                document.body.style.setProperty("width", "500px");
                window.dispatchEvent(new Event("resize"));
            },
        },
        {
            trigger: ".o_automation_actions:contains(Set Active To False 2 actions)",
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_resequence_actions", {
    steps: () => [
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_renderer",
            async run() {
                assertEqual(
                    this.anchor.innerText,
                    "Update Active 0\nUpdate Active 1\nUpdate Active 2"
                );
            },
        },
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_record:nth-child(3)",
            run: "drag_and_drop(.o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_record:nth-child(1))",
        },
        ...stepUtils.saveForm(),
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_renderer",
            async run() {
                assertEqual(
                    this.anchor.innerText,
                    "Update Active 2\nUpdate Active 0\nUpdate Active 1"
                );
            },
        },
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_view .o_cp_buttons button",
            run: "click",
        },
        {
            trigger: ".modal-content .o_form_renderer",
            run() {
                const allFields = this.anchor.querySelectorAll(".o_field_widget[name]");
                assertEqual(
                    Array.from(allFields)
                        .map((el) => el.getAttribute("name"))
                        .includes("model_id"),
                    false
                );
            },
        },
        {
            trigger: ".modal-content .o_form_renderer [name='state'] span[value*='followers']",
            run: "click",
        },
        {
            trigger:
                ".modal-content .o_form_renderer [name='state'] span.active[value*='followers']",
        },
        {
            trigger: ".modal-content .o_form_button_cancel",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal-content))",
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_model_id", {
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit base.automation.line.test",
        },
        {
            trigger: ".dropdown-menu li a:contains(Automated Rule Line Test)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='trigger'] input",
            run: "click",
        },
        {
            trigger: ".o_select_menu_menu",
            run() {
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_group"))
                        .map((el) => el.textContent)
                        .join(", "),
                    "Values Updated, Timing Conditions, Custom, External"
                );
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_item"))
                        .map((el) => el.textContent)
                        .join(", "),
                    "User is set, Based on date field, After creation, After last update, On create, On create and edit, On deletion, On UI change, On webhook"
                );
            }
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit test_base_automation.project",
        },
        {
            trigger: ".dropdown-menu li a:contains(test_base_automation.project)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='trigger'] input",
            run: "click",
        },
        {
            trigger: ".o_select_menu_menu",
            run() {
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_group"))
                        .map((el) => el.textContent)
                        .join(", "),
                    "Values Updated, Timing Conditions, Custom, External"
                );
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_item"))
                        .map((el) => el.textContent)
                        .join(", "),
                    "Stage is set to, User is set, Tag is added, Priority is set to, Based on date field, After creation, After last update, On create, On create and edit, On deletion, On UI change, On webhook"
                );
            }
        },
        {
            trigger: ".o_form_button_cancel",
            run: "click",
        },
        {
            trigger: ".o_base_automation_kanban_view",
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_custom_reference_field", {
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit test_base_automation.project",
        },
        {
            trigger: ".dropdown-menu li a:contains(test_base_automation.project)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.o_field_widget[name='trg_field_ref']))",
        },
        {
            content: "Open select",
            trigger: ".o_form_renderer #trigger_0",
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:contains(Stage is set to)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='trg_field_ref'] input",
            run: "fill test",
        },
        {
            trigger:
                ".o_field_widget[name='trg_field_ref'] .o-autocomplete--dropdown-menu:not(:has(a .fa-spin)",
            run() {
                assertEqual(this.anchor.innerText, "test stage\nSearch more...");
            },
        },
        {
            content: "Open select",
            trigger: ".o_form_renderer #trigger_0",
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:contains(Tag is added)",
            run: "click",
        },
        {
            trigger:
                ".o_field_widget[name='trg_field_ref'] :not(:has(.o-autocomplete--dropdown-menu))",
        },
        {
            trigger: ".o_field_widget[name='trg_field_ref'] input",
            run: "fill test",
        },
        {
            trigger:
                ".o_field_widget[name='trg_field_ref'] .o-autocomplete--dropdown-menu:not(:has(a .fa-spin)",
            run() {
                assertEqual(this.anchor.innerText, "test tag\nSearch more...");
            },
        },
        {
            trigger: ".o_form_button_cancel",
            run: "click",
        },
        {
            trigger: ".o_base_automation_kanban_view",
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_mail_triggers", {
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit base.automation.lead.test",
        },
        {
            trigger: ".dropdown-menu li a:contains(Automated Rule Test)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='trigger'] input",
            run: "click",
        },
        {
            trigger: ".o_select_menu_menu",
            run() {
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_group"))
                        .map((el) => el.textContent)
                        .join(", "),
                    "Values Updated, Timing Conditions, Custom, External"
                );
            },
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit base.automation.lead.thread.test",
        },
        {
            trigger: ".dropdown-menu li a:contains(Threaded Lead Test)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='trigger'] input",
            run: "click",
        },
        {
            trigger: ".o_select_menu_menu",
            run() {
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_group "))
                        .map((el) => el.textContent)
                        .join(", "),
                    "Values Updated, Email Events, Timing Conditions, Custom, External"
                );
            }
        },
        {
            trigger: "button.o_form_button_cancel",
            run: "click",
        },
        {
            trigger: "body:not(:has(button.o_form_button_cancel)",
        },
    ],
});

registry.category("web_tour.tours").add("base_automation.on_change_rule_creation", {
    url: "/odoo/action-base_automation.base_automation_act",
    steps: () => [
        {
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=name] input",
            run: "edit Test rule",
        },
        {
            trigger: ".o_field_widget[name=model_id] input",
            run: "edit ir.ui.view",
        },
        {
            trigger: ".ui-menu-item > a:text(View)",
            run: "click",
        },
        {
            content: "Open select",
            trigger: ".o_form_renderer #trigger_0",
            run: "click",
        },
        {
            trigger: ".o_select_menu_item:contains(On UI change)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name=on_change_field_ids] input",
            run: "edit Active",
        },
        {
            trigger: ".ui-menu-item > a:text(Active)",
            run: "click",
        },
        ...stepUtils.saveForm(),
    ],
});
