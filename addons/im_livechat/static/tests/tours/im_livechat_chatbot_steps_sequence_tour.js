import { registry } from "@web/core/registry";

import { stepUtils } from "@web_tour/tour_service/tour_utils";

const commonSteps = [
    stepUtils.showAppsMenuItem(),
    {
        trigger: '.o_app[data-menu-xmlid="im_livechat.menu_livechat_root"]',
        run: "click",
    },
    {
        trigger: 'button[data-menu-xmlid="im_livechat.livechat_config"]',
        run: "click",
    },
    {
        trigger: 'a[data-menu-xmlid="im_livechat.chatbot_config"]',
        run: "click",
    },
    {
        trigger: ".o_list_button_add",
        run: "click",
    },
    {
        trigger: 'input[id="title_0"]',
        run: "edit Test Chatbot Sequence",
    },
    {
        trigger: 'div[name="script_step_ids"] .o_field_x2many_list_row_add a',
        run: "click",
    },
    {
        trigger: ".modal textarea#message_0",
        run: "edit Step 1",
    },
    {
        trigger: ".modal button:contains(Save & New):enabled",
        run: "click",
    },
    {
        trigger: 'tr:contains("Step 1")',
    },
    {
        trigger: ".modal textarea#message_0",
        run: "edit Step 2",
    },
    {
        trigger: ".modal button:contains(Save & New):enabled",
        run: "click",
    },
    {
        trigger: 'tr:contains("Step 2")',
    },
    {
        trigger: ".modal textarea#message_0",
        run: "edit Step 3",
    },
];

/**
 * Simply create a few steps in order to check the sequences.
 */
registry.category("web_tour.tours").add("im_livechat_chatbot_steps_sequence_tour", {
    url: "/odoo",
    steps: () => [
        ...commonSteps,
        {
            trigger: ".modal button:contains(Save & Close)",
            run: "click",
        },
        {
            trigger: "body.o_web_client:not(.modal-open)",
        },
    ],
});

/**
 * Same as above, with an extra drag&drop at the end.
 */
registry.category("web_tour.tours").add("im_livechat_chatbot_steps_sequence_with_move_tour", {
    url: "/odoo",
    steps: () => [
        ...commonSteps,
        {
            trigger: ".modal button:contains(Save & New)",
            run: "click",
        },
        {
            trigger: 'tr:contains("Step 3")',
        },
        {
            trigger: ".modal textarea#message_0",
            run: "edit Step 4",
        },
        {
            trigger: 'button:contains("Save & New")',
            run: "click",
        },
        {
            trigger: 'tr:contains("Step 4")',
        },
        {
            trigger: ".modal textarea#message_0",
            run: "edit Step 5",
        },
        {
            trigger: ".modal button:contains(Save & Close)",
            run: "click",
        },
        {
            trigger: "body.o_web_client:not(.modal-open)",
        },
        {
            trigger: 'div[name="script_step_ids"] tr:nth-child(5) .o_row_handle',
            run: 'drag_and_drop(div[name="script_step_ids"] tr:nth-child(2))',
        },
        {
            trigger: 'div[name="script_step_ids"] .o_field_x2many_list_row_add a',
            run: "click",
        },
        {
            trigger: ".modal textarea#message_0",
            run: "edit Step 6",
        },
        {
            trigger: ".modal button:contains(Save & Close)",
            run: "click",
        },
        {
            trigger: "body.o_web_client:not(.modal-open)",
        },
        {
            trigger: 'tr:contains("Step 6")',
        },
    ],
});
