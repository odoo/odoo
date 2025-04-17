import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("event_question_answers_rule_creation_tour", {
    url: "/odoo",
    steps: () => [
        ...stepUtils.goToAppSteps("event.event_main_menu"),
        {
            content: "Click on the Configuration menu.",
            trigger: 'button[data-menu-xmlid="event.menu_event_configuration"]',
            run: "click",
        },
        {
            content: "Go to the list of questions.",
            trigger: 'a[data-menu-xmlid="event.event_question_menu"]',
            run: "click",
        },
        {
            content: "Go to the form of a specific question.",
            trigger: 'td[name="title"]:contains("Question Test")',
            run: "click",
        },
        {
            content: "Click on the 'Add rule' button.",
            trigger: 'tr:contains("Answer Test") button[name="action_add_rule_button"]',
            run: "click",
        },
        {
            content: "Edit the name of the rule.",
            trigger: "[name=name] input",
            run: "edit event_question_answer_rule",
        },
        {
            content: "Save the rule creation form with pre-filled data, except for the name.",
            trigger: '.modal:contains("Event lead rule") .o_form_button_save',
            run: "click",
        },
        {
            content: "Wait until the modal is closed",
            trigger: "body:not(.modal-open)",
        },
    ],
});
