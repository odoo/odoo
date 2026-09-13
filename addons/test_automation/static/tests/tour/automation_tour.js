import { rpc } from "@web/core/network";
import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

function assertEqual(actual, expected) {
    if (actual !== expected) {
        throw new Error(`Assert failed: expected: ${expected} ; got: ${actual}`);
    }
}

registry.category("web_tour.tours").add("test_automation", {
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
            trigger:
                ".o_model_field_selector_popover .o_model_field_selector_popover_search input",
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

registry.category("web_tour.tours").add("test_automation_on_tag_added", {
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
            run: "edit test_automation.project",
        },
        {
            trigger:
                ".dropdown-menu li a:contains(test_automation.project):not(:has(.fa-spin))",
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
                // Compare as a set, not an ordered list: the tour's contract is
                // *which* triggers a model offers, not the order the selection
                // happens to be declared in. Pinning the order made adding a
                // trigger (this fork's "Manual trigger") a tour failure.
                const options = [
                    ...this.anchor.querySelectorAll(".o_select_menu_item"),
                ].map((el) => el.textContent);

                assertEqual(
                    JSON.stringify([...options].sort()),
                    JSON.stringify(
                        [
                            "After creation",
                            "After last update",
                            "Based on date field",
                            "Manual trigger",
                            "On UI change",
                            "On create",
                            "On create and edit",
                            "On deletion",
                            "On webhook",
                            "Priority is set to",
                            "Stage is set to",
                            "Tag is added",
                            "User is set",
                        ].sort(),
                    ),
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
            trigger: ".o_automation_kanban_view .o_kanban_record",
            run() {
                assertEqual(
                    this.anchor.querySelector(".o_automation_base_info").textContent,
                    "Test ruletest_automation.projectTag is addedtest",
                );
                assertEqual(
                    this.anchor.querySelector(".o_automation_actions").textContent,
                    "Update test_automation.projectUpdate test_automation.project",
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
            trigger:
                ".o_automation_kanban_view .o_control_panel button.o-kanban-button-new",
            run: "click",
        },
        {
            trigger: ".o_form_view",
            run() {
                assertEqual(
                    this.anchor.querySelector(".o_field_widget[name='trigger'] input")
                        .value,
                    "Tag is added",
                );
                assertEqual(
                    this.anchor.querySelector(
                        ".o_field_widget[name='trg_field_ref'] input",
                    ).value,
                    "test tag",
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
            trigger: ".o_automation_kanban_view",
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
            trigger: ".o_automation_kanban_view",
        },
        {
            trigger:
                ".o_automation_base_info > div > div > span:nth-child(1):contains(1)",
        },
        {
            trigger: ".o_automation_base_info .text-lowercase:contains(hours)",
        },
        {
            trigger: `.o_kanban_record .o_tag:contains("Last Automation (Automated Rule Test)")`,
        },
    ],
});

registry
    .category("web_tour.tours")
    .add("test_kanban_automation_view_time_updated_trigger", {
        steps: () => [
            {
                trigger: ".o_automation_kanban_view",
            },
            {
                trigger:
                    ".o_automation_base_info > div > div > span:nth-child(1):contains(1)",
                async run() {
                    const lowercaseTexts = document.querySelectorAll(
                        ".o_automation_base_info .text-lowercase",
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
            trigger: ".o_automation_kanban_view",
        },
        {
            trigger:
                "div[name='action_server_ids']:contains(Create Contact with name NameX)",
            async run() {
                // Font Awesome 6 class for the object_create action icon; this
                // module's widget template moved off the FA4 names
                // (fa-plus-square, fa-user-times, fa-clock-o, ...) wholesale.
                assertEqual(
                    document.querySelectorAll(".fa-solid.fa-square-plus").length,
                    1,
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_resize_kanban", {
    steps: () => [
        {
            trigger: ".o_automation_kanban_view",
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
                    "Update Active 0\nUpdate Active 1\nUpdate Active 2",
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
                    "Update Active 2\nUpdate Active 0\nUpdate Active 1",
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
                    false,
                );
            },
        },
        {
            trigger:
                ".modal-content .o_form_renderer [name='state'] span[value*='followers']",
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
            run: "edit automation.line.test",
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
                    "Values Updated, Timing Conditions, Custom, External",
                );
                // Compare as a set, not an ordered list: the tour's contract is
                // *which* triggers a model offers, not the order the selection
                // happens to be declared in. Pinning the order made adding a
                // trigger (this fork's "Manual trigger") a tour failure.
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_item"))
                        .map((el) => el.textContent)
                        .sort()
                        .join(", "),
                    [
                        "User is set",
                        "Based on date field",
                        "After creation",
                        "After last update",
                        "On UI change",
                        "On create",
                        "On create and edit",
                        "Manual trigger",
                        "On deletion",
                        "On webhook",
                    ]
                        .sort()
                        .join(", "),
                );
            },
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit test_automation.project",
        },
        {
            trigger: ".dropdown-menu li a:contains(test_automation.project)",
            run: "click",
        },
        {
            trigger: ".o_field_widget[name='trigger'] input",
            run: "click",
        },
        {
            // The widget reads the model's fields over RPC and offers nothing
            // until they land, so wait for a trigger only this model has before
            // reading the whole list.
            content: "wait for the menu to reflect the new model",
            trigger: ".o_select_menu_item:contains(Stage is set to)",
        },
        {
            trigger: ".o_select_menu_menu",
            run() {
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_group"))
                        .map((el) => el.textContent)
                        .join(", "),
                    "Values Updated, Timing Conditions, Custom, External",
                );
                // Compare as a set, not an ordered list: the tour's contract is
                // *which* triggers a model offers, not the order the selection
                // happens to be declared in. Pinning the order made adding a
                // trigger (this fork's "Manual trigger") a tour failure.
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_item"))
                        .map((el) => el.textContent)
                        .sort()
                        .join(", "),
                    [
                        "Stage is set to",
                        "User is set",
                        "Tag is added",
                        "Priority is set to",
                        "Based on date field",
                        "After creation",
                        "After last update",
                        "On UI change",
                        "On create",
                        "On create and edit",
                        "Manual trigger",
                        "On deletion",
                        "On webhook",
                    ]
                        .sort()
                        .join(", "),
                );
            },
        },
        {
            trigger: ".o_form_button_cancel",
            run: "click",
        },
        {
            trigger: ".o_automation_kanban_view",
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_custom_reference_field", {
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit test_automation.project",
        },
        {
            trigger: ".dropdown-menu li a:contains(test_automation.project)",
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
                ".o_field_widget[name='trg_field_ref'] .o-autocomplete--dropdown-menu:not(:has(.o_loading))",
            run() {
                // Assert the record is offered, not the dropdown's chrome:
                // "Search more..." only appears once the results exceed the
                // display limit, so pinning it made the assertion depend on how
                // many stages happen to exist in the database.
                assertEqual(this.anchor.innerText.includes("test stage"), true);
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
                ".o_field_widget[name='trg_field_ref']:not(:has(.o-autocomplete--dropdown-menu))",
        },
        {
            trigger: ".o_field_widget[name='trg_field_ref'] input",
            run: "fill test",
        },
        {
            trigger:
                ".o_field_widget[name='trg_field_ref'] .o-autocomplete--dropdown-menu:not(:has(.o_loading))",
            run() {
                // See the "test stage" assertion above: "Search more..." is a
                // function of how many records exist, not of this behaviour.
                assertEqual(this.anchor.innerText.includes("test tag"), true);
            },
        },
        {
            trigger: ".o_form_button_cancel",
            run: "click",
        },
        {
            trigger: ".o_automation_kanban_view",
        },
    ],
});

registry.category("web_tour.tours").add("test_form_view_mail_triggers", {
    steps: () => [
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit automation.lead.test",
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
                    "Values Updated, Timing Conditions, Custom, External",
                );
            },
        },
        {
            trigger: ".o_field_widget[name='model_id'] input",
            run: "edit automation.lead.thread.test",
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
            // Wait for the group this model adds, for the same reason.
            content: "wait for the menu to reflect the threaded model",
            trigger: ".o_select_menu_group:contains(Email Events)",
        },
        {
            trigger: ".o_select_menu_menu",
            run() {
                assertEqual(
                    Array.from(this.anchor.querySelectorAll(".o_select_menu_group "))
                        .map((el) => el.textContent)
                        .join(", "),
                    "Values Updated, Email Events, Timing Conditions, Custom, External",
                );
            },
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

registry.category("web_tour.tours").add("automation.on_change_rule_creation", {
    url: "/odoo/action-automation.automation_act",
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

function openWorkflowTab() {
    return [
        {
            content: "open the Workflow tab",
            trigger: ".o_notebook .nav-link:contains(Workflow)",
            run: "click",
        },
        {
            // The canvas is tall and sits low in the form, so on a short window
            // its lower half is out of view and a pointer aimed at a port there
            // lands on nothing at all. A reader scrolls to it; so does this.
            content: "bring the canvas into view",
            trigger: ".o_workflow_canvas_paper",
            run() {
                document
                    .querySelector(".o_workflow_canvas_paper")
                    .scrollIntoView({ block: "center" });
            },
        },
    ];
}

registry.category("web_tour.tours").add("test_workflow_canvas", {
    steps: () => [
        ...openWorkflowTab(),
        {
            content: "the flow editor drew the graph",
            trigger: ".o_workflow_canvas_paper .o_flow_editor_connections",
            run() {
                const paper = document.querySelector(".o_workflow_canvas_paper");
                assertEqual(
                    paper.querySelectorAll(".o_workflow_canvas_node").length,
                    3,
                );
                assertEqual(
                    paper.querySelectorAll(".o_workflow_canvas_link").length,
                    2,
                );
            },
        },
        {
            content: "the edges are drawn in their condition's colour",
            trigger: ".o_workflow_canvas_paper .o_workflow_canvas_on_error",
            run() {
                const paper = document.querySelector(".o_workflow_canvas_paper");
                assertEqual(
                    paper.querySelectorAll(".o_workflow_canvas_on_success").length,
                    1,
                );
                assertEqual(
                    paper.querySelectorAll(".o_workflow_canvas_on_error").length,
                    1,
                );
            },
        },
        {
            content: "auto-layout placed the nodes apart rather than stacking them",
            trigger: ".o_workflow_canvas_paper .o_flow_editor_node",
            run() {
                const positions = Array.from(
                    document.querySelectorAll(
                        ".o_workflow_canvas_paper .o_flow_editor_node",
                    ),
                ).map((el) => el.getAttribute("style"));
                assertEqual(positions.length, 3);
                assertEqual(new Set(positions).size, 3);
            },
        },
        {
            content: "the step names reached the canvas",
            trigger: ".o_workflow_canvas_step_header:contains(first)",
            run() {
                // Every step accepts an input, so the editor finds no source node
                // and would call all three unreachable if the flag were left on.
                assertEqual(
                    document.querySelectorAll(".o_flow_editor_node_disconnected")
                        .length,
                    0,
                );
                assertEqual(document.querySelectorAll(".o_flow_editor_node").length, 3);
            },
        },
        {
            content: "tidy up re-runs the layout without losing the graph",
            trigger: ".o_workflow_canvas_toolbar button:contains(Tidy up)",
            run: "click",
        },
        {
            trigger: ".o_workflow_canvas_paper .o_flow_editor_connections",
            run() {
                const paper = document.querySelector(".o_workflow_canvas_paper");
                assertEqual(
                    paper.querySelectorAll(".o_workflow_canvas_node").length,
                    3,
                );
            },
        },
        {
            content: "the step count is reported",
            trigger: ".o_workflow_canvas_toolbar:contains(3 steps)",
        },
    ],
});

registry.category("web_tour.tours").add("test_workflow_canvas_edit", {
    steps: () => [
        ...openWorkflowTab(),
        {
            content: "wait for the graph",
            trigger: ".o_workflow_canvas_paper .o_workflow_canvas_link",
        },
        {
            content: "nothing is selected, so removal is unavailable",
            trigger:
                ".o_workflow_canvas_toolbar button:contains(Remove connection)[disabled]",
        },
        {
            // The hitbox path, not the group: it carries a 12px transparent
            // stroke, so it has a box a tour can call visible where a straight
            // horizontal edge's own 1.5px path does not.
            content: "select a connection",
            trigger: ".o_workflow_canvas_link .o_flow_editor_connection_hitbox",
            run: "click",
        },
        {
            content: "selecting one enables removal",
            trigger:
                ".o_workflow_canvas_toolbar button:contains(Remove connection):not([disabled])",
            run: "click",
        },
        {
            content: "the payload came back with one connection fewer",
            trigger: ".o_workflow_canvas_toolbar:contains(3 steps, 1 connections)",
        },
        {
            content: "and the canvas redrew itself with exactly that one",
            // Triggering on the host, not on the link: a tour trigger requires a
            // *visible* element, and a horizontal edge is only as tall as its
            // stroke. querySelectorAll inside run() does not care.
            trigger: ".o_workflow_canvas_paper > div",
            run() {
                // The widget's own classes: one per connection, one per step.
                assertEqual(
                    document.querySelectorAll(
                        ".o_workflow_canvas_paper .o_workflow_canvas_link",
                    ).length,
                    1,
                );
                assertEqual(
                    document.querySelectorAll(
                        ".o_workflow_canvas_paper .o_workflow_canvas_node",
                    ).length,
                    3,
                );
                // One canvas, not the old one with a new one stacked on it.
                assertEqual(
                    document.querySelectorAll(".o_workflow_canvas_paper > div").length,
                    1,
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_workflow_canvas_remove_step", {
    steps: () => [
        ...openWorkflowTab(),
        {
            content: "wait for the graph",
            trigger: ".o_workflow_canvas_paper .o_workflow_canvas_link",
            run() {
                // "second" is the middle step, so removing it removes both
                // edges: the cascade on workflow.edge's node fields, and the
                // editor's follow-up disconnect for each of them.
                assertEqual(
                    document.querySelectorAll(
                        ".o_workflow_canvas_paper .o_workflow_canvas_link",
                    ).length,
                    2,
                );
            },
        },
        {
            content: "the step a run already reached withholds its remove button",
            trigger: ".o_workflow_canvas_paper .o_flow_editor_node",
            run() {
                const withHeader = (name) =>
                    [
                        ...document.querySelectorAll(
                            ".o_workflow_canvas_paper .o_flow_editor_node",
                        ),
                    ].find((node) =>
                        node
                            .querySelector(".o_workflow_canvas_step_header")
                            ?.textContent.includes(name),
                    );
                assertEqual(
                    Boolean(
                        withHeader("third").querySelector(".o_flow_editor_node_delete"),
                    ),
                    false,
                );
                assertEqual(
                    Boolean(
                        withHeader("second").querySelector(
                            ".o_flow_editor_node_delete",
                        ),
                    ),
                    true,
                );
            },
        },
        {
            content: "remove the middle step",
            trigger:
                ".o_flow_editor_node:has(.o_workflow_canvas_step_header:contains(second))" +
                " .o_flow_editor_node_delete",
            run: "click",
        },
        {
            content: "the step and both of its connections are gone",
            trigger: ".o_workflow_canvas_toolbar:contains(2 steps, 0 connections)",
        },
        {
            content: "and the canvas redrew without them",
            trigger: ".o_workflow_canvas_paper > div",
            run() {
                assertEqual(
                    document.querySelectorAll(
                        ".o_workflow_canvas_paper .o_workflow_canvas_node",
                    ).length,
                    2,
                );
                assertEqual(
                    document.querySelectorAll(
                        ".o_workflow_canvas_paper .o_workflow_canvas_link",
                    ).length,
                    0,
                );
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_workflow_canvas_remove_last_step", {
    steps: () => [
        ...openWorkflowTab(),
        {
            content: "remove the only step",
            trigger: ".o_flow_editor_node .o_flow_editor_node_delete",
            run: "click",
        },
        {
            // The editor is swapped for the widget's own guidance, which says
            // what to do next where the editor's generic "No nodes" does not.
            content: "the canvas gives way to the empty-workflow message",
            trigger: ".o_workflow_canvas:contains(This automation has no steps yet)",
            run() {
                assertEqual(document.querySelectorAll(".o_flow_editor").length, 0);
                assertEqual(document.querySelectorAll(".o_error_dialog").length, 0);
            },
        },
        {
            content: "and the count went with it",
            trigger: ".o_workflow_canvas_toolbar:contains(0 steps, 0 connections)",
        },
    ],
});

registry.category("web_tour.tours").add("test_workflow_canvas_drag", {
    steps: () => [
        ...openWorkflowTab(),
        {
            content: "wait for the graph",
            trigger: ".o_workflow_canvas_paper > div",
            run() {
                assertEqual(
                    document.querySelectorAll(
                        ".o_workflow_canvas_paper .o_workflow_canvas_node",
                    ).length,
                    2,
                );
            },
        },
        {
            content: "remember where the first step is",
            trigger: ".o_workflow_canvas_paper .o_workflow_canvas_node",
            run() {
                window.__wfBefore = document
                    .querySelectorAll(".o_workflow_canvas_paper .o_flow_editor_node")[0]
                    .getAttribute("style");
            },
        },
        {
            // The step's own body, which is what a real pointer lands on; the
            // editor's drag handler sits on the article above it.
            content: "drag it onto the second one",
            trigger: ".o_workflow_canvas_paper .o_workflow_canvas_node:first",
            async run(helpers) {
                await helpers.drag_and_drop(
                    ".o_workflow_canvas_paper .o_workflow_canvas_node:last",
                );
            },
        },
        {
            content: "the drag moved that step",
            trigger: ".o_workflow_canvas_paper > div",
            run() {
                const after = document
                    .querySelectorAll(".o_workflow_canvas_paper .o_flow_editor_node")[0]
                    .getAttribute("style");
                if (after === window.__wfBefore) {
                    throw new Error(`the drag did not move the step: still ${after}`);
                }
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_workflow_canvas_resize", {
    steps: () => [
        ...openWorkflowTab(),
        {
            content: "wait for the graph",
            trigger: ".o_workflow_canvas_paper .o_flow_editor_node",
            run() {
                window.__wfSize = document
                    .querySelectorAll(".o_workflow_canvas_paper .o_flow_editor_node")[0]
                    .getAttribute("style");
                // The lowest output port's hit area reaches into this corner,
                // so whichever of the two wins here decides whether a pointer
                // resizes the step or starts drawing a connection from it.
                const handle = document.querySelector(
                    ".o_flow_editor_node .o_flow_editor_node_resize_handle",
                );
                const box = handle.getBoundingClientRect();
                const atCorner = document.elementFromPoint(
                    box.left + box.width / 2,
                    box.top + box.height / 2,
                );
                if (
                    !atCorner ||
                    !atCorner.closest(".o_flow_editor_node_resize_handle")
                ) {
                    throw new Error(
                        `the resize corner is covered by ${atCorner && atCorner.className}`,
                    );
                }
            },
        },
        {
            // Onto the second step, which the fixture placed down and to the
            // right: the resize reads the pointer rather than what sits under
            // it, so the far step is just a coordinate to aim at.
            content: "drag the first step's resize handle away from itself",
            trigger: ".o_flow_editor_node:first .o_flow_editor_node_resize_handle",
            async run(helpers) {
                // Hover first: drag_and_drop presses at the pointer's CURRENT
                // position and only then travels to the trigger, so without
                // this the gesture starts wherever the last step left the
                // pointer -- which was below the handle, making the drag read
                // as a shrink and pinning the step to its minimum height.
                await helpers.hover(
                    ".o_flow_editor_node:first .o_flow_editor_node_resize_handle",
                );
                // And an explicit drop point inside the far step: the bare form
                // drops one pixel ABOVE its top edge, which is also upward.
                await helpers.drag_and_drop(".o_flow_editor_node:last", {
                    position: { top: 40, left: 60 },
                    relative: true,
                });
            },
        },
        {
            content: "the step grew",
            trigger: ".o_workflow_canvas_paper .o_flow_editor_node",
            run() {
                const after = document
                    .querySelectorAll(".o_workflow_canvas_paper .o_flow_editor_node")[0]
                    .getAttribute("style");
                if (after === window.__wfSize) {
                    throw new Error(`the drag did not resize the step: still ${after}`);
                }
            },
        },
        {
            content: "pan the canvas, which is what a viewport is saved from",
            trigger: ".o_workflow_canvas_paper .o_flow_editor",
            async run(helpers) {
                await helpers.drag_and_drop(".o_workflow_canvas_toolbar");
            },
        },
        {
            content: "the graph survived both gestures",
            trigger: ".o_workflow_canvas_toolbar:contains(2 steps)",
        },
        {
            // The viewport is saved behind a debounce, and a tour finishes far
            // inside that window, so waiting for the ROW is the only thing that
            // makes this deterministic: a fixed sleep would race the timer and
            // ending here without waiting would race the request.
            content: "the viewport the canvas framed reaches the database",
            trigger: ".o_workflow_canvas_toolbar",
            async run() {
                for (let attempt = 0; attempt < 40; attempt++) {
                    const stored = await rpc("/web/dataset/call_kw", {
                        model: "automation.canvas.viewport",
                        method: "search_count",
                        args: [[]],
                        kwargs: {},
                    });
                    if (stored) {
                        return;
                    }
                    await new Promise((resolve) => setTimeout(resolve, 100));
                }
                throw new Error("the canvas never stored a viewport");
            },
        },
    ],
});

registry.category("web_tour.tours").add("test_workflow_canvas_connect", {
    steps: () => [
        ...openWorkflowTab(),
        {
            content: "three steps, one connection",
            trigger: ".o_workflow_canvas_toolbar:contains(3 steps, 1 connections)",
        },
        {
            // drag_and_drop always starts from the trigger element -- the helper
            // reads `this.anchor` and ignores any source passed in options -- so
            // the trigger must be the port we are dragging FROM.
            // Port to port: the editor resolves the drop with elementFromPoint
            // and accepts it only over an input port, so dropping on the step's
            // body would connect nothing.
            content: "drag a connection from the last step to the first",
            trigger:
                ".o_flow_editor_node:last .o_flow_editor_port_output[data-port-id='on_success']",
            async run(helpers) {
                await helpers.drag_and_drop(
                    ".o_flow_editor_node:first .o_flow_editor_port_input",
                );
            },
        },
        {
            content: "the canvas came back with the new connection",
            trigger: ".o_workflow_canvas_toolbar:contains(3 steps, 2 connections)",
        },
    ],
});
