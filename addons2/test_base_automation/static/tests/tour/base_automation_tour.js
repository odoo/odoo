/** @odoo-module */
import { ORM } from "@web/core/orm_service";
import { patch } from "@web/core/utils/patch";

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

function assertEqual(actual, expected) {
    if (actual !== expected) {
        throw new Error(`Assert failed: expected: ${expected} ; got: ${actual}`);
    }
}

async function nextTick() {
    await new Promise(setTimeout);
    await new Promise(requestAnimationFrame);
}

function observeOrmCalls() {
    const calls = [];

    const unpatch = patch(ORM.prototype, {
        call() {
            const prom = super.call(...arguments);
            calls.push([prom, arguments]);
            return prom;
        },
    });

    async function wait(unobserve = true) {
        await Promise.all(calls.map((i) => i[0]));
        if (unobserve) {
            unpatch();
        }
    }
    return wait;
}

registry.category("web_tour.tours").add("test_base_automation", {
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Create new rule",
            trigger: ".o_control_panel button.o-kanban-button-new",
        },
        {
            content: "Enter rule name",
            trigger: ".o_form_renderer .oe_title .o_input",
            run: "text Test rule",
        },
        {
            content: "Select model",
            trigger: '.o_form_renderer .o_group div[name="model_id"] input',
            run: "text res.partner",
        },
        {
            content: "Select model contact",
            extra_trigger:
                '.o_form_renderer .o_group div[name="model_id"] .dropdown-menu:contains(Contact)',
            trigger:
                '.o_form_renderer .o_group div[name="model_id"] .dropdown-menu li a:contains(Contact):not(:has(.fa-spin))',
        },
        {
            content: "Open select",
            trigger: ".o_form_renderer #trigger_0",
        },
        {
            content: "Select On save",
            trigger: ".o_form_renderer #trigger_0",
            run: `text "on_create_or_write"`,
        },
        {
            content: "Add new action",
            trigger: '.o_form_renderer div[name="action_server_ids"] button',
        },
        {
            content: "Set new action to update the record",
            trigger: ".modal-content .o_form_renderer [name='state'] span[value*='object_write']",
        },
        {
            content: "Focus on the 'update_path' field",
            trigger: ".modal-content .o_form_renderer [name='update_path'] .o_model_field_selector",
        },
        {
            content: "Input field name",
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_search  input',
            run: "text Job Position",
            in_modal: false,
        },
        {
            content: "Select field",
            in_modal: false,
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_page li[data-name="function"] button',
        },
        {
            content: "Open update select",
            trigger: '.modal-content .o_form_renderer div[name="value"] textarea',
            run: "text Test",
        },
        {
            content: "Open update select",
            trigger: ".modal-content .o_form_button_save",
        },
        ...stepUtils.saveForm({
            extra_trigger: ".o-overlay-container:not(:has(.modal-content))",
        }),
    ],
});

registry.category("web_tour.tours").add("test_base_automation_on_tag_added", {
    test: true,
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            trigger: ".o_control_panel button.o-kanban-button-new",
        },
        {
            trigger: ".o_form_renderer .oe_title .o_input",
            run: "text Test rule",
        },
        {
            trigger: '.o_form_renderer .o_group div[name="model_id"] input',
            run: "text test_base_automation.project",
        },
        {
            trigger:
                '.o_form_renderer .o_group div[name="model_id"] .dropdown-menu li a:contains(test_base_automation.project):not(:has(.fa-spin))',
        },
        {
            trigger: ".o_form_renderer #trigger_0",
            run() {
                const options = Object.fromEntries(
                    Array.from(this.$anchor[0].querySelectorAll("option")).map((el) => [
                        JSON.parse(el.value),
                        el.textContent,
                    ])
                );

                assertEqual(
                    JSON.stringify(options),
                    JSON.stringify({
                        false: "",
                        on_stage_set: "Stage is set to",
                        on_user_set: "User is set",
                        on_tag_set: "Tag is added",
                        on_priority_set: "Priority is set to",
                        on_time: "Based on date field",
                        on_time_created: "After creation",
                        on_time_updated: "After last update",
                        on_create_or_write: "On save",
                        on_unlink: "On deletion",
                        on_change: "On UI change",
                        on_webhook: "On webhook",
                    })
                );
            },
        },
        {
            trigger: ".o_form_renderer #trigger_0",
            run: 'text "on_tag_set"',
        },
        {
            trigger: '.o_form_renderer div[name="trg_field_ref"] input',
            run: "text test",
        },
        {
            trigger:
                '.o_form_renderer div[name="trg_field_ref"] .dropdown-menu li a:contains(test):not(:has(.fa-spin))',
        },
        {
            trigger: '.o_form_renderer div[name="action_server_ids"] button',
        },
        {
            trigger: " .modal-content .o_form_renderer [name='state'] span[value*='object_write']",
        },
        {
            content: "Focus on the 'update_path' field",
            trigger: ".modal-content .o_form_renderer [name='update_path'] .o_model_field_selector",
        },
        {
            content: "Input field name",
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_search  input',
            run: "text Name",
            in_modal: false,
        },
        {
            content: "Select field",
            in_modal: false,
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_page li[data-name="name"] button',
        },
        {
            trigger: '.modal-content .o_form_renderer div[name="value"] textarea',
            run: "text Test",
        },
        {
            trigger: ".modal-content .o_form_button_save",
        },
        {
            trigger: '.o_form_renderer div[name="action_server_ids"] button',
        },
        {
            trigger: " .modal-content .o_form_renderer [name='state'] span[value*='object_write']",
        },
        {
            content: "Focus on the 'update_path' field",
            trigger: ".modal-content .o_form_renderer [name='update_path'] .o_model_field_selector",
        },
        {
            content: "Input field name",
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_search  input',
            run: "text Priority",
            in_modal: false,
        },
        {
            content: "Select field",
            in_modal: false,
            trigger:
                '.o_model_field_selector_popover .o_model_field_selector_popover_page li[data-name="priority"] button',
        },
        {
            trigger: '.modal-content .o_form_renderer div[name="selection_value"] input',
            run: "text High",
        },
        {
            trigger:
                '.modal-content .o_form_renderer div[name="selection_value"] .dropdown-menu li a:contains(High):not(:has(.fa-spin))',
        },
        {
            trigger: ".modal-content .o_form_button_save",
        },
        ...stepUtils.saveForm({
            extra_trigger: ".o-overlay-container:not(:has(.modal-content))",
        }),
        {
            trigger: ".breadcrumb .o_back_button a",
        },
        {
            trigger: ".o_base_automation_kanban_view .o_kanban_record",
            run() {
                const card = this.$anchor[0];
                assertEqual(
                    card.querySelector(".o_automation_base_info").textContent,
                    "Test ruletest_base_automation.projectTag is addedtest"
                );
                assertEqual(
                    card.querySelector(".o_automation_actions").textContent,
                    "Update NameUpdate Priority"
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_open_automation_from_grouped_kanban", {
    test: true,
    steps: () => [
        {
            trigger: ".o_kanban_view .o-dropdown.o_kanban_config button",
        },
        {
            trigger: ".o_kanban_view .o-dropdown.o_kanban_config .o_column_automations",
        },
        {
            trigger: ".o_base_automation_kanban_view .o_control_panel button.o-kanban-button-new",
        },
        {
            trigger: ".o_form_view",
            run() {
                const form = this.$anchor[0];
                assertEqual(
                    form.querySelector(".o_field_widget[name='trigger'] select").value,
                    '"on_tag_set"'
                );
                assertEqual(
                    form.querySelector(".o_field_widget[name='trg_field_ref'] input").value,
                    "test tag"
                );
            },
        },
        {
            trigger: ".o_form_view .o_field_widget[name='name'] input",
            run: "text From Tour",
        },
        ...stepUtils.saveForm(),
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_stage_trigger", {
    test: true,
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
            async run() {
                assertEqual(
                    document.querySelector(".o_kanban_record .fs-2").innerText,
                    "Test Stage"
                );
                assertEqual(
                    document.querySelector(".o_kanban_record .o_tag").innerText,
                    "Stage value"
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_time_trigger", {
    test: true,
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
            async run() {
                assertEqual(
                    document.querySelector(
                        ".o_automation_base_info > div > div > span:nth-child(1)"
                    ).innerText,
                    "1"
                );
                assertEqual(
                    document.querySelector(".o_automation_base_info .text-lowercase").innerText,
                    "hours"
                );
                assertEqual(
                    document.querySelector(".o_kanban_record .o_tag").innerText,
                    "Date (Contact)"
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_time_updated_trigger", {
    test: true,
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
            async run() {
                const lowercaseTexts = document.querySelectorAll(
                    ".o_automation_base_info .text-lowercase"
                );
                const number = document.querySelector(
                    ".o_automation_base_info > div > div > span:nth-child(1)"
                ).innerText;
                assertEqual(number, "1");
                assertEqual(lowercaseTexts.length, 2);
                assertEqual(lowercaseTexts[0].innerText, "hours");
                assertEqual(lowercaseTexts[1].innerText, "after last update");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_kanban_automation_view_create_action", {
    test: true,
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
            async run() {
                assertEqual(
                    document.querySelector("div[name='action_server_ids']").innerText,
                    "Create Contact with name NameX"
                );
                assertEqual(document.querySelectorAll(".fa.fa-edit").length, 1);
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_resize_kanban", {
    test: true,
    steps: () => [
        {
            trigger: ".o_base_automation_kanban_view",
            async run() {
                assertEqual(
                    this.$anchor[0].querySelector(".o_automation_actions").innerText,
                    "Set Active To False\nSet Active To False\nSet Active To False"
                );
                document.body.style.setProperty("width", "500px");
                window.dispatchEvent(new Event("resize"));
                await nextTick();
                await nextTick();
                assertEqual(
                    this.$anchor[0].querySelector(".o_automation_actions").innerText,
                    "Set Active To False\n2 actions"
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_resequence_actions", {
    test: true,
    steps: () => [
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_renderer",
            async run() {
                assertEqual(
                    this.$anchor[0].innerText,
                    "Update Active 0\nto\nNo (False)\nUpdate Active 1\nto\nNo (False)\nUpdate Active 2\nto\nNo (False)"
                );
            },
        },
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_record:nth-child(3)",
            run: "drag_and_drop_native (.o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_record:nth-child(1))",
        },
        ...stepUtils.saveForm(),
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_renderer",
            async run() {
                assertEqual(
                    this.$anchor[0].innerText,
                    "Update Active 2\nto\nNo (False)\nUpdate Active 0\nto\nNo (False)\nUpdate Active 1\nto\nNo (False)"
                );
            },
        },
        {
            trigger:
                ".o_form_renderer .o_field_widget[name='action_server_ids'] .o_kanban_view .o_cp_buttons button",
        },
        {
            trigger: ".modal-content .o_form_renderer",
            run() {
                const allFields = this.$anchor[0].querySelectorAll(".o_field_widget[name]");
                assertEqual(
                    Array.from(allFields)
                        .map((el) => el.getAttribute("name"))
                        .includes("model_id"),
                    false
                );
            },
        },
        {
            trigger: ".modal-content .o_form_renderer [name='state'] span[value*='object_write']",
        },
        {
            trigger: ".modal-content .o_form_renderer [name='state'] span[value*='followers']",
        },
        {
            extra_trigger:
                ".modal-content .o_form_renderer [name='state'] span.active[value*='followers']",
            trigger: ".modal-content .o_form_button_cancel",
        },
        {
            extra_trigger: "body:not(:has(.modal-content))",
            trigger: ".o_form_button_cancel",
            isCheck: true,
        },
    ],
});

let waitOrmCalls;
registry.category("web_tour.tours").add("test_form_view_model_id", {
    test: true,
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "text base.automation.line.test",
        },
        {
            trigger:
                ".o_field_widget[name='model_id'] .dropdown-menu li a:contains(Automated Rule Line Test)",
        },
        {
            trigger: ".o_field_widget[name='trigger']",
            run() {
                const triggerGroups = Array.from(this.$anchor[0].querySelectorAll("optgroup"));
                assertEqual(
                    triggerGroups.map((el) => el.getAttribute("label")).join(" // "),
                    "Values Updated // Timing Conditions // Custom // External"
                );
                assertEqual(
                    triggerGroups.map((el) => el.innerText).join(" // "),
                    "User is set // Based on date fieldAfter creationAfter last update // On saveOn deletionOn UI change // On webhook"
                );
            },
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "text test_base_automation.project",
        },
        {
            trigger:
                ".o_field_widget[name='model_id'] .dropdown-menu li a:contains(test_base_automation.project)",
            run(helpers) {
                waitOrmCalls = observeOrmCalls();
                helpers.click(this.$anchor);
                return nextTick();
            },
        },
        {
            trigger: "body",
            async run() {
                await waitOrmCalls();
                await nextTick();
            },
        },
        {
            trigger: ".o_field_widget[name='trigger']",
            run() {
                const triggerGroups = Array.from(this.$anchor[0].querySelectorAll("optgroup"));
                assertEqual(
                    triggerGroups.map((el) => el.getAttribute("label")).join(" // "),
                    "Values Updated // Timing Conditions // Custom // External"
                );
                assertEqual(
                    triggerGroups.map((el) => el.innerText).join(" // "),
                    "Stage is set toUser is setTag is addedPriority is set to // Based on date fieldAfter creationAfter last update // On saveOn deletionOn UI change // On webhook"
                );
            },
        },
        {
            trigger: ".o_form_button_cancel",
        },
        {
            trigger: ".o_base_automation_kanban_view",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_custom_reference_field", {
    test: true,
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "text test_base_automation.project",
        },
        {
            trigger:
                ".o_field_widget[name='model_id'] .dropdown-menu li a:contains(test_base_automation.project)",
        },
        {
            extra_trigger: "body:not(:has(.o_field_widget[name='trg_field_ref']))",
            trigger: ".o_field_widget[name='trigger'] select",
            run: 'text "on_stage_set"',
        },
        {
            trigger: ".o_field_widget[name='trg_field_ref'] input",
        },
        {
            trigger:
                ".o_field_widget[name='trg_field_ref'] .o-autocomplete--dropdown-menu:not(:has(a .fa-spin)",
            run() {
                assertEqual(this.$anchor[0].innerText, "test stage\nSearch More...");
            },
        },
        {
            trigger: ".o_field_widget[name='trigger'] select",
            run: 'text "on_tag_set"',
        },
        {
            trigger:
                ".o_field_widget[name='trg_field_ref'] :not(:has(.o-autocomplete--dropdown-menu))",
            isCheck: true,
        },
        {
            trigger: ".o_field_widget[name='trg_field_ref'] input",
        },
        {
            trigger:
                ".o_field_widget[name='trg_field_ref'] .o-autocomplete--dropdown-menu:not(:has(a .fa-spin)",
            run() {
                assertEqual(this.$anchor[0].innerText, "test tag\nSearch More...");
            },
        },
        {
            trigger: ".o_form_button_cancel",
        },
        {
            trigger: ".o_base_automation_kanban_view",
            isCheck: true,
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_mail_triggers", {
    test: true,
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "text base.automation.lead.test",
        },
        {
            trigger:
                ".o_field_widget[name='model_id'] .dropdown-menu li a:contains(Automated Rule Test)",
        },
        {
            trigger: ".o_field_widget[name='trigger'] select",
            run() {
                assertEqual(Array.from(this.$anchor[0].querySelectorAll("optgroup")).map(el => el.label).join(", "), "Values Updated, Timing Conditions, Custom, External")
            }
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "text base.automation.lead.thread.test",
        },
        {
            trigger:
                ".o_field_widget[name='model_id'] .dropdown-menu li a:contains(Threaded Lead Test)",
            run(helpers) {
                waitOrmCalls = observeOrmCalls();
                helpers.click(this.$anchor);
                return nextTick();
            },
        },
        {
            trigger: "body",
            async run() {
                await waitOrmCalls();
                await nextTick();
            },
        },
        {
            trigger: ".o_field_widget[name='trigger']",
            run() {
                assertEqual(Array.from(this.$anchor[0].querySelectorAll("select optgroup")).map(el => el.label).join(", "), "Values Updated, Email Events, Timing Conditions, Custom, External")
            }
        },
        {
            trigger: "button.o_form_button_cancel",
        },
        {
            trigger: "body:not(:has(button.o_form_button_cancel)",
            run() {}
        }
    ],
});

registry.category("web_tour.tours").add('base_automation.on_change_rule_creation', {
    test: true,
    url: "/web#action=base_automation.base_automation_act",
    steps: () => [
    {
        trigger: ".o-kanban-button-new",
    }, {
        trigger: ".o_field_widget[name=name] input",
        run: "text Test rule",
    }, {
        trigger: ".o_field_widget[name=model_id] input",
        run: "text ir.ui.view",
    }, {
        trigger: ".ui-menu-item > a:containsExact('View')",
    }, {
        trigger: ".o_field_widget[name=trigger] select",
        run: 'text "on_change"',
    }, {
        trigger: ".o_field_widget[name=on_change_field_ids] input",
        run: "text Active",
    }, {
        trigger: ".ui-menu-item > a:containsExact('Active')",
    },
    ...stepUtils.saveForm(),
]});
